import { json, request } from "./client";
import type { Preference, SavedPreferencePrompt } from "./types";

export const savePreferences = (body: Preference) => json<{ message: string }>("/preferences/", "POST", body);
export const getPreferences = () => request<Preference | null>("/preferences/");
export const preferenceChoice = () => request<SavedPreferencePrompt>("/preferences/choice-prompt");
