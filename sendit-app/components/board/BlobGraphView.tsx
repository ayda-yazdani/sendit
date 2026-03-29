import { useMemo, useRef } from "react";
import { View, StyleSheet, useWindowDimensions, Text } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { forceCollide, forceSimulation, forceX, forceY } from "d3-force";
import { ActivityBlob, getBlobSize } from "./ActivityBlob";
import { theme } from "@/constants/Theme";

const MAX_BLOBS = 6;
const DEFAULT_CATEGORY = "vibe_inspiration";
const KNOWN_CATEGORIES = new Set([
  "real_event",
  "competition",
  "real_venue",
  "recipe_food",
  "sports_fitness",
  "outdoor_adventure",
  "arts_culture",
  "travel_explore",
  "shopping_style",
  "gaming",
  "vibe_inspiration",
  "humour_identity",
]);

function normalizeCategory(value: string | null | undefined): string {
  if (!value) return DEFAULT_CATEGORY;
  if (value === "uncategorised" || value === "other") return DEFAULT_CATEGORY;
  return KNOWN_CATEGORIES.has(value) ? value : DEFAULT_CATEGORY;
}

interface Reel {
  id: string;
  url: string;
  platform: string;
  extraction_data: any;
  classification: string | null;
  created_at: string;
}

interface BlobCluster {
  category: string;
  reels: { id: string; title?: string; thumbnail_url?: string }[];
  count: number;
  reelIds: string[];
}

interface BlobGraphViewProps {
  reels: Reel[];
  onBlobPress: (category: string, reels: Reel[]) => void;
  width?: number;
  height?: number;
  reactedReelIds?: Set<string> | string[] | null;
}

// Cluster reels by classification
function clusterReels(reels: Reel[]): BlobCluster[] {
  const groups: Record<string, Reel[]> = {};

  for (const reel of reels) {
    const cat = normalizeCategory(reel.classification);
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(reel);
  }

  const clusters = Object.entries(groups)
    .map(([category, categoryReels]) => ({
      category,
      reels: categoryReels.map((r) => ({
        id: r.id,
        title: r.extraction_data?.title,
        thumbnail_url: r.extraction_data?.thumbnail_url,
      })),
      count: categoryReels.length,
      reelIds: categoryReels.map((r) => r.id),
    }))
    .sort((a, b) => b.count - a.count); // Largest first

  return clusters.slice(0, MAX_BLOBS);
}

// Position blobs in a natural-feeling layout
// Uses a simple circle packing approach centred on screen
function layoutBlobs(
  clusters: BlobCluster[],
  sizes: number[],
  width: number,
  height: number,
): { x: number; y: number }[] {
  if (clusters.length === 0 || width <= 0 || height <= 0) return [];

  const centerX = width / 2;
  const centerY = height / 2;
  const padding = 18;

  const nodes = clusters.map((_, index) => ({
    index,
    radius: sizes[index] / 2,
    x: centerX,
    y: centerY,
  }));

  const simulation = forceSimulation(nodes)
    .force("x", forceX(centerX).strength(0.05))
    .force("y", forceY(centerY).strength(0.05))
    .force(
      "collide",
      forceCollide<{ radius: number }>().radius((d) => d.radius + 18).iterations(3),
    )
    .stop();

  for (let i = 0; i < 200; i += 1) simulation.tick();

  return nodes.map((node) => ({
    x: Math.min(width - padding - node.radius, Math.max(padding + node.radius, node.x || centerX)),
    y: Math.min(height - padding - node.radius, Math.max(padding + node.radius, node.y || centerY)),
  }));
}

export function BlobGraphView({
  reels,
  onBlobPress,
  width,
  height,
  reactedReelIds,
}: BlobGraphViewProps) {
  const { width: windowWidth, height: windowHeight } = useWindowDimensions();
  const graphWidth = Math.max(1, width ?? windowWidth);
  const graphHeight = Math.max(1, height ?? Math.max(260, windowHeight - 220));

  const clusters = useMemo(() => clusterReels(reels), [reels]);
  const orderRef = useRef<string[]>([]);
  const orderedClusters = useMemo(() => {
    const nextCategories = clusters.map((cluster) => cluster.category);
    const nextSet = new Set(nextCategories);

    const existing = orderRef.current.filter((cat) => nextSet.has(cat));
    const additions = nextCategories.filter((cat) => !existing.includes(cat));
    orderRef.current = [...existing, ...additions];

    const indexByCategory = new Map(orderRef.current.map((cat, idx) => [cat, idx]));
    return [...clusters].sort(
      (a, b) => (indexByCategory.get(a.category) ?? 0) - (indexByCategory.get(b.category) ?? 0)
    );
  }, [clusters]);
  const hasReactionData = reactedReelIds !== undefined && reactedReelIds !== null;
  const reactedSet = useMemo(() => {
    if (!hasReactionData) return new Set<string>();
    return reactedReelIds instanceof Set ? reactedReelIds : new Set(reactedReelIds);
  }, [reactedReelIds, hasReactionData]);
  const reelMap = useMemo(() => new Map(reels.map((reel) => [reel.id, reel])), [reels]);
  const sizeBounds = useMemo(() => {
    const maxSize = Math.min(180, Math.round(graphWidth * 0.42));
    const minSize = Math.min(120, Math.round(graphWidth * 0.28));
    return {
      min: Math.max(90, minSize),
      max: Math.max(140, maxSize),
    };
  }, [graphWidth]);

  const blobSizes = useMemo(
    () => orderedClusters.map((cluster) => getBlobSize(cluster.count, sizeBounds.min, sizeBounds.max)),
    [orderedClusters, sizeBounds],
  );

  const positions = useMemo(
    () => layoutBlobs(orderedClusters, blobSizes, graphWidth, graphHeight),
    [orderedClusters, blobSizes, graphWidth, graphHeight],
  );

  return (
    <View style={[styles.container, { width: graphWidth, height: graphHeight }]}>
      <LinearGradient
        colors={["rgba(40,75,99,0.25)", "rgba(0,0,0,0.8)"]}
        style={StyleSheet.absoluteFill}
        start={{ x: 0.2, y: 0 }}
        end={{ x: 0.8, y: 1 }}
        pointerEvents="none"
      />
      {orderedClusters.map((cluster, index) => (
        <ActivityBlob
          key={cluster.category}
          category={cluster.category}
          reelCount={cluster.count}
          reels={cluster.reels}
          x={positions[index]?.x ?? graphWidth / 2}
          y={positions[index]?.y ?? graphHeight / 2}
          index={index}
          minSize={sizeBounds.min}
          maxSize={sizeBounds.max}
          hasNotification={hasReactionData && cluster.reelIds.some((id) => !reactedSet.has(id))}
          onPress={() => {
            const clusterReelsFull = cluster.reelIds
              .map((id) => reelMap.get(id))
              .filter((reel): reel is Reel => Boolean(reel));
            onBlobPress(cluster.category, clusterReelsFull);
          }}
        />
      ))}

      {/* Empty state when no reels */}
      {reels.length === 0 && (
        <View style={styles.emptyContainer}>
          <View style={styles.emptyBlob}>
            <View style={styles.emptyPulse} />
          </View>
          <Text style={styles.emptyText}>Paste a link to create your first bubble</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "relative",
  },
  emptyContainer: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
  },
  emptyBlob: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: "rgba(152, 38, 73, 0.15)",
    alignItems: "center",
    justifyContent: "center",
  },
  emptyPulse: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: "rgba(152, 38, 73, 0.25)",
  },
  emptyText: {
    marginTop: 14,
    fontSize: 13,
    color: theme.colors.textSecondary,
    textAlign: "center",
  },
});
