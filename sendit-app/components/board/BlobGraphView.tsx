import { useMemo } from "react";
import { View, StyleSheet, Dimensions } from "react-native";
import { ActivityBlob } from "./ActivityBlob";

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");
const GRAPH_HEIGHT = SCREEN_HEIGHT - 200; // Leave room for header + URL input

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
}

interface BlobGraphViewProps {
  reels: Reel[];
  onBlobPress: (category: string, reels: Reel[]) => void;
}

// Cluster reels by classification
function clusterReels(reels: Reel[]): BlobCluster[] {
  const groups: Record<string, Reel[]> = {};

  for (const reel of reels) {
    const cat = reel.classification || "uncategorised";
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(reel);
  }

  return Object.entries(groups)
    .map(([category, categoryReels]) => ({
      category,
      reels: categoryReels.map((r) => ({
        id: r.id,
        title: r.extraction_data?.title,
        thumbnail_url: r.extraction_data?.thumbnail_url,
      })),
      count: categoryReels.length,
    }))
    .sort((a, b) => b.count - a.count) // Largest first
    .slice(0, 5); // Max 5 blobs
}

// Position blobs in a natural-feeling layout
// Uses a simple circle packing approach centred on screen
function layoutBlobs(clusters: BlobCluster[]): { x: number; y: number }[] {
  const centerX = SCREEN_WIDTH / 2;
  const centerY = GRAPH_HEIGHT / 2;

  if (clusters.length === 0) return [];
  if (clusters.length === 1) return [{ x: centerX, y: centerY }];

  const positions: { x: number; y: number }[] = [];
  const radius = Math.min(SCREEN_WIDTH, GRAPH_HEIGHT) * 0.28;

  for (let i = 0; i < clusters.length; i++) {
    if (i === 0) {
      // Largest blob near centre (slightly offset for organic feel)
      positions.push({ x: centerX - 10, y: centerY - 20 });
    } else {
      // Distribute remaining blobs in a circle around centre
      const angle = ((i - 1) / (clusters.length - 1)) * Math.PI * 2 - Math.PI / 2;
      // Add some jitter for organic feel
      const jitterX = (Math.sin(i * 7.3) * 20);
      const jitterY = (Math.cos(i * 5.1) * 15);
      positions.push({
        x: centerX + Math.cos(angle) * radius + jitterX,
        y: centerY + Math.sin(angle) * radius + jitterY,
      });
    }
  }

  return positions;
}

export function BlobGraphView({ reels, onBlobPress }: BlobGraphViewProps) {
  const clusters = useMemo(() => clusterReels(reels), [reels]);
  const positions = useMemo(() => layoutBlobs(clusters), [clusters]);

  return (
    <View style={[styles.container, { height: GRAPH_HEIGHT }]}>
      {clusters.map((cluster, index) => (
        <ActivityBlob
          key={cluster.category}
          category={cluster.category}
          reelCount={cluster.count}
          reels={cluster.reels}
          x={positions[index]?.x ?? SCREEN_WIDTH / 2}
          y={positions[index]?.y ?? GRAPH_HEIGHT / 2}
          index={index}
          onPress={() => {
            const clusterReelsFull = reels.filter(
              (r) => (r.classification || "uncategorised") === cluster.category
            );
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
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: SCREEN_WIDTH,
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
});
