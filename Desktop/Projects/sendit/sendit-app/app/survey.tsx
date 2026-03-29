import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  Dimensions,
  ScrollView,
  ActivityIndicator,
  Alert,
} from "react-native";
import { router } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { BlurView } from "expo-blur";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import { theme } from "@/constants/Theme";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/lib/stores/auth-store";

const { width: SCREEN_WIDTH } = Dimensions.get("window");

interface SurveyStep {
  question: string;
  subtitle: string;
  tags: string[];
  gradient: [string, string];
}

const STEPS: SurveyStep[] = [
  {
    question: "What are you into?",
    subtitle: "Pick as many as you like",
    tags: ["Cooking", "Photography", "Gaming", "Reading", "Art", "Fitness", "Travel", "Music", "Film", "Fashion", "Tech", "Nature", "Dance", "Writing", "DIY", "Yoga", "Skating", "Gardening", "Thrifting", "Podcasts"],
    gradient: ["#982649", "#D8A48F"],
  },
  {
    question: "Ideal weekend activity?",
    subtitle: "What sounds like your kind of day",
    tags: ["Brunch", "Museum", "Club Night", "Hiking", "Beach", "Shopping", "Cinema", "Pub", "Board Games", "Road Trip", "Concert", "Picnic", "Market", "Karaoke", "Spa Day", "Rooftop Bar", "Street Food Tour", "Comedy Show", "Gallery", "House Party"],
    gradient: ["#3C6E71", "#94C595"],
  },
  {
    question: "What's your energy?",
    subtitle: "How would your friends describe you",
    tags: ["Chill", "Laid-back", "Go with the flow", "Spontaneous", "Energetic", "Chaotic", "Unhinged", "Night owl", "Early riser", "Low-key"],
    gradient: ["#284B63", "#3C6E71"],
  },
  {
    question: "Music or partying?",
    subtitle: "Or both, we don't judge",
    tags: ["Live Music", "DJ Sets", "House Parties", "Intimate Dinners", "Late Night Talks", "Bar Hopping", "Raves", "Acoustic Nights", "Silent Discos", "Wine Bars"],
    gradient: ["#D8A48F", "#982649"],
  },
  {
    question: "What do you watch?",
    subtitle: "Your screen time says a lot",
    tags: ["Sci-Fi", "Comedy", "True Crime", "Reality TV", "Anime", "Documentaries", "Horror", "Drama", "Romance", "Indie Film", "Action", "Stand-up", "K-Drama", "Thriller", "Fantasy"],
    gradient: ["#94C595", "#284B63"],
  },
  {
    question: "Food preferences?",
    subtitle: "The important question",
    tags: ["Japanese", "Italian", "Mexican", "Indian", "Thai", "Korean", "Chinese", "Mediterranean", "Street Food", "Vegan", "BBQ", "Brunch Spots", "Desserts", "Ramen", "Burgers", "Seafood", "Middle Eastern", "Ethiopian", "French", "Fusion"],
    gradient: ["#982649", "#3C6E71"],
  },
  {
    question: "What's your vibe?",
    subtitle: "Pick your aesthetic",
    tags: ["Minimalist", "Cosy", "Underground", "Bougie", "Vintage", "Streetwear", "Cottagecore", "Dark Academia", "Y2K", "Clean Girl", "Indie Sleaze", "Goblincore", "Old Money", "Coastal", "Grunge"],
    gradient: ["#3C6E71", "#D8A48F"],
  },
  {
    question: "Price range?",
    subtitle: "No judgement here",
    tags: ["Free stuff", "Under £10", "£10-20", "£20-40", "£40+", "Depends on the mood", "Split the bill", "Treat myself", "Budget-friendly", "No limit"],
    gradient: ["#284B63", "#982649"],
  },
  {
    question: "Where do you hang?",
    subtitle: "Your usual spots",
    tags: ["City Centre", "East London", "South London", "Suburbs", "Countryside", "Seaside", "Rooftops", "Basements", "Parks", "Anywhere with WiFi", "Home", "Cafes", "Markets", "Warehouses"],
    gradient: ["#D8A48F", "#94C595"],
  },
  {
    question: "What makes you laugh?",
    subtitle: "Last one, we promise",
    tags: ["Memes", "Dry wit", "Sarcasm", "Absurdist", "Dad jokes", "Dark humour", "Slapstick", "Satire", "Self-deprecating", "Surreal", "Wholesome", "Cringe", "Political", "Niche Internet", "Brainrot"],
    gradient: ["#982649", "#284B63"],
  },
];

export default function SurveyScreen() {
  const [stepIndex, setStepIndex] = useState(0);
  const [selections, setSelections] = useState<Record<number, string[]>>({});
  const [saving, setSaving] = useState(false);
  const { session } = useAuthStore();

  const step = STEPS[stepIndex];
  const selected = selections[stepIndex] || [];

  const toggleTag = (tag: string) => {
    setSelections((prev) => {
      const current = prev[stepIndex] || [];
      const next = current.includes(tag)
        ? current.filter((t) => t !== tag)
        : [...current, tag];
      return { ...prev, [stepIndex]: next };
    });
  };

  const handleNext = () => {
    if (stepIndex < STEPS.length - 1) {
      setStepIndex((prev) => prev + 1);
    } else {
      handleComplete();
    }
  };

  const handleBack = () => {
    if (stepIndex > 0) setStepIndex((prev) => prev - 1);
  };

  const handleComplete = async () => {
    setSaving(true);
    try {
      // Build the taste vector from all selections
      const tasteVector = STEPS.map((s, i) => ({
        category: s.question,
        selections: selections[i] || [],
      }));

      // Save to user metadata in Supabase Auth
      await supabase.auth.updateUser({
        data: {
          taste_survey: tasteVector,
          survey_completed: true,
        },
      });

      router.replace("/(tabs)");
    } catch (error: any) {
      Alert.alert("Error", error.message);
    } finally {
      setSaving(false);
    }
  };

  const progress = (stepIndex + 1) / STEPS.length;

  return (
    <View style={styles.container}>
      {/* Background gradient */}
      <LinearGradient
        colors={[step.gradient[0] + "40", step.gradient[1] + "20", "#000"]}
        style={StyleSheet.absoluteFill}
        start={{ x: 0.3, y: 0 }}
        end={{ x: 0.7, y: 1 }}
      />

      {/* Progress bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${progress * 100}%`, backgroundColor: step.gradient[0] }]} />
        </View>
        <Text style={styles.progressText}>{stepIndex + 1}/{STEPS.length}</Text>
      </View>

      {/* Back button */}
      {stepIndex > 0 && (
        <Pressable style={styles.backButton} onPress={handleBack}>
          <FontAwesome name="chevron-left" size={16} color={theme.colors.text} />
        </Pressable>
      )}

      {/* Question */}
      <View style={styles.questionContainer}>
        <Text style={styles.question}>{step.question}</Text>
        <Text style={styles.subtitle}>{step.subtitle}</Text>
      </View>

      {/* Tag cloud — glassmorphism style */}
      <ScrollView
        style={styles.tagScroll}
        contentContainerStyle={styles.tagCloud}
        showsVerticalScrollIndicator={false}
      >
        {step.tags.map((tag) => {
          const isSelected = selected.includes(tag);
          return (
            <Pressable
              key={tag}
              onPress={() => toggleTag(tag)}
              style={[
                styles.tag,
                isSelected && { backgroundColor: step.gradient[0] + "50", borderColor: step.gradient[0] },
              ]}
            >
              <Text style={[
                styles.tagText,
                isSelected && { color: theme.colors.text, fontFamily: theme.fonts.bold },
              ]}>
                {tag}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>

      {/* Next / Finish button */}
      <View style={styles.bottomBar}>
        {selected.length > 0 && (
          <Text style={styles.selectedCount}>
            {selected.length} selected
          </Text>
        )}
        <Pressable
          style={[styles.nextButton, { backgroundColor: step.gradient[0] }]}
          onPress={handleNext}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator color={theme.colors.text} />
          ) : (
            <Text style={styles.nextText}>
              {stepIndex === STEPS.length - 1 ? "Finish" : "Next"}
            </Text>
          )}
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
  },

  // Progress
  progressContainer: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: 60,
    gap: 10,
  },
  progressTrack: {
    flex: 1,
    height: 3,
    backgroundColor: "rgba(255,255,255,0.1)",
    borderRadius: 2,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: 2,
  },
  progressText: {
    fontSize: 12,
    fontFamily: theme.fonts.regular,
    color: "#666",
  },

  // Back
  backButton: {
    position: "absolute",
    top: 56,
    left: 20,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.08)",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 10,
  },

  // Question
  questionContainer: {
    paddingHorizontal: 24,
    paddingTop: 32,
    paddingBottom: 20,
  },
  question: {
    fontSize: 28,
    fontFamily: theme.fonts.bold,
    color: theme.colors.text,
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 15,
    fontFamily: theme.fonts.regular,
    color: "#888",
  },

  // Tags
  tagScroll: {
    flex: 1,
    paddingHorizontal: 20,
  },
  tagCloud: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    paddingBottom: 20,
  },
  tag: {
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1.5,
    borderColor: "rgba(255,255,255,0.08)",
  },
  tagText: {
    fontSize: 15,
    fontFamily: theme.fonts.semibold,
    color: "#aaa",
  },

  // Bottom
  bottomBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 24,
    paddingVertical: 20,
    paddingBottom: 40,
  },
  selectedCount: {
    fontSize: 13,
    fontFamily: theme.fonts.regular,
    color: "#666",
  },
  nextButton: {
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 24,
    shadowColor: "#982649",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 10,
    elevation: 8,
  },
  nextText: {
    fontSize: 16,
    fontFamily: theme.fonts.bold,
    color: theme.colors.text,
  },
});
