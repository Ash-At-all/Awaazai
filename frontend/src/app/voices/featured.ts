export interface FeaturedVoiceConfig {
  order: number;
  id: string;
  display_name: string;
  reference_id: string;
  label: string;
  provider: "fish";
  tone: string;
  accent: string;
  avatar_color: string;
  sample_text: string;
}

export const FEATURED_VOICES_CONFIG: FeaturedVoiceConfig[] = [
  {
    order: 1,
    id: "fish_narration",
    display_name: "Narration",
    reference_id: "0de8162a9e384545a0106046b57488a7",
    label: "Narration",
    provider: "fish",
    tone: "Storytelling & Audiobooks",
    accent: "गंभीर एवं स्पष्ट हिंदी",
    avatar_color: "from-sky-500 to-blue-700",
    sample_text: "नमस्ते, आवाज़ एआई में आपका स्वागत है। चलिए एक नई और शानदार कहानी की शुरुआत करते हैं।",
  },
  {
    order: 2,
    id: "fish_indian_girl",
    display_name: "Indian Girl (19)",
    reference_id: "2b9e2a84cb664489a7ab9ca71af5dff5",
    label: "Indian girl, 19 years",
    provider: "fish",
    tone: "Conversational & Friendly",
    accent: "नेचुरल और मीठी आवाज़",
    avatar_color: "from-pink-500 to-rose-600",
    sample_text: "हेलो, आवाज़ एआई पर आपका स्वागत है! क्या आज हम कुछ नया और एक्साइटिंग बनाएं?",
  },
  {
    order: 3,
    id: "fish_gojo",
    display_name: "Gojo",
    reference_id: "528f686ef2154885b368dd4b93fb8728",
    label: "Gojo-style character",
    provider: "fish",
    tone: "Cool & Energetic",
    accent: "स्टाइलिश और दमदार",
    avatar_color: "from-indigo-500 to-violet-700",
    sample_text: "फिक्र मत करो, जब तक मैं यहाँ हूँ, सब एकदम परफेक्ट होगा!",
  },
  {
    order: 4,
    id: "fish_funny_man",
    display_name: "Funny Man",
    reference_id: "d219c65920e540509486a30373f5c5c0",
    label: "Middle-aged funny man",
    provider: "fish",
    tone: "Humorous & Comedy",
    accent: "मज़ेदार और ड्रामैटिक",
    avatar_color: "from-amber-500 to-orange-600",
    sample_text: "अरे अरे भाई साहब! मुस्कुराइए, क्योंकि अब आवाज़ एआई का जलवा शुरू होने वाला है!",
  },
];
