export type User = {
  id: string;
  name: string;
  email: string;
  profile_picture_version?: string | null;
  has_password: boolean;
  google_connected: boolean;
};
export type TokenResponse = { access_token: string; token_type: string };
export type GoogleAuthConfig = { enabled: boolean; client_id: string | null; csrf_token: string | null };
export type Health = { status: string; database: string };

export type Preference = {
  travel_style: string;
  food_preference: string;
  interests: string[];
  preferred_transport: string;
  preferred_hotel_type: string;
  budget_min: number;
  budget_max: number;
};

export type SavedPreferencePrompt = {
  has_saved_preferences: boolean;
  message: string;
  saved_preferences?: Preference | null;
};

export type Trip = {
  id: string;
  start_location: string;
  destination: string;
  start_date: string;
  end_date: string;
  budget_min: number;
  budget_max: number;
  travelers: number;
  transport_type: string;
  created_at?: string;
  updated_at?: string;
};

export type Place = {
  place_key: string;
  name: string;
  source?: string;
  category: string;
  short_description?: string | null;
  reason_for_recommendation?: string | null;
  best_time_to_visit?: string | null;
  estimated_visit_duration_hours?: number | null;
  estimated_cost_lkr_per_person?: number | null;
  priority_score?: number | null;
  suitable_for?: string[];
  warnings?: string[];
  opening_hours?: string | null;
  availability_warnings?: string[];
  search_query?: string | null;
  weather_summary?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  image_url?: string | null;
  display_name?: string;
  osm_type?: string;
  osm_id?: number;
};

export type DestinationResponse = {
  trip_id: string;
  destination: string;
  summary: string;
  suggested_places: Place[];
  question_for_user?: string;
};

export type Hotel = {
  hotel_key: string;
  name: string;
  short_description?: string | null;
  hotel_type: string;
  source?: string;
  area?: string | null;
  check_in_date?: string | null;
  check_out_date?: string | null;
  nights?: number;
  rooms?: number;
  estimated_price_per_night_lkr?: number;
  total_estimated_price_lkr?: number;
  rating_estimate?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  distance_summary?: string | null;
  reason_for_recommendation?: string | null;
  amenities?: string[];
  warnings?: string[];
  search_query?: string | null;
  image_url?: string | null;
  priority_score?: number | null;
  day_number?: number | null;
  route_plan_id?: string | null;
  transfer_distance_km?: number;
  transfer_time_minutes?: number;
  transfer_cost_lkr?: number;
};

export type HotelResponse = {
  trip_id: string;
  destination: string;
  nights: number;
  rooms: number;
  summary: string;
  recommended_hotels: Hotel[];
  question_for_user?: string;
};

export type Coordinate = { latitude: number; longitude: number };
export type RouteStop = {
  place_key?: string;
  name: string;
  category?: string;
  date?: string;
  day_number?: number;
  arrival_time?: string;
  start_time?: string;
  end_time?: string;
  best_time_to_visit?: string | null;
  visit_duration_hours?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  travel_time_from_previous_minutes?: number | null;
  travel_distance_from_previous_km?: number | null;
  note?: string | null;
  opening_hours?: string | null;
  availability_warnings?: string[];
};
export type RouteSegment = {
  from_name: string;
  to_name: string;
  start_time?: string;
  end_time?: string;
  distance_km?: number;
  duration_minutes?: number;
  transport_cost_lkr?: number;
  transport_cost_source?: string;
  fare_per_person_lkr?: number | null;
  passenger_count?: number;
  fare_is_live?: boolean;
  encoded_polyline?: string | null;
  path_coordinates?: Coordinate[];
  instructions?: { instruction: string; distance_km?: number; duration_minutes?: number }[];
};
export type RouteDay = {
  day_number: number;
  date: string;
  start_time?: string;
  end_time?: string;
  start_point_name?: string;
  end_point_name?: string;
  stops: RouteStop[];
  segments: RouteSegment[];
  day_distance_km?: number;
  day_travel_time_minutes?: number;
  day_transport_cost_lkr?: number;
  day_encoded_polyline?: string | null;
  day_path_coordinates?: Coordinate[];
};
export type RoutePlan = {
  trip_id: string;
  destination?: string;
  start_date?: string;
  end_date?: string;
  transport_type?: string;
  total_distance_km?: number;
  total_travel_time_minutes?: number;
  total_transport_cost_lkr?: number;
  full_encoded_polyline?: string | null;
  days: RouteDay[];
  map_provider?: string;
  route_status?: "draft" | "confirmed" | string;
  summary?: string;
};

export type ManualRouteStop = {
  place_key: string;
  day_number: number;
  start_time?: string | null;
  visit_duration_hours?: number | null;
};

export type DailyHotelResponse = {
  trip_id: string;
  day_number: number;
  route_plan_id: string;
  suggestions: Hotel[];
  summary: string;
};

export type Budget = {
  trip_id: string;
  destination: string;
  days: number;
  nights: number;
  travelers: number;
  budget_min_lkr: number;
  budget_max_lkr: number;
  selected_places_cost_lkr: number;
  hotel_cost_lkr: number;
  food_cost_lkr: number;
  transport_cost_lkr: number;
  other_cost_lkr: number;
  subtotal_lkr: number;
  buffer_lkr: number;
  total_estimated_cost_lkr: number;
  remaining_budget_lkr: number;
  over_budget_amount_lkr: number;
  budget_status: "within_budget" | "near_limit" | "over_budget";
  breakdown: { category: string; description: string; amount_lkr: number }[];
  warnings: string[];
  suggestions: string[];
  summary: string;
};

export type ChecklistItem = {
  id: string;
  label: string;
  completed: boolean;
};

export type TripExpense = {
  id: string;
  description: string;
  amount_lkr: number;
  category: "accommodation" | "food" | "transport" | "activities" | "shopping" | "other";
  paid_by: string;
  expense_date?: string | null;
};

export type TripToolkit = {
  trip_id: string;
  traveler_notes: string;
  emergency_contact: string;
  checklist: ChecklistItem[];
  expenses: TripExpense[];
  total_expenses_lkr: number;
};

export type TripToolkitInput = Omit<TripToolkit, "trip_id" | "total_expenses_lkr">;

export type Review = {
  id?: string;
  place_name: string;
  place_type: string;
  rating: number;
  review_text: string;
  visit_date: string;
};

export type PlanningJob = {
  id: string;
  trip_id: string;
  kind: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  current_stage: string;
  result?: Record<string, unknown> | null;
  error?: string | null;
  cancel_requested: boolean;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  updated_at: string;
};

export type TripVersion = {
  id: string;
  trip_id: string;
  version_number: number;
  label: string;
  created_at: string;
};

export type Collaborator = {
  id: string;
  user_id: string;
  name: string;
  email: string;
  role: "viewer" | "editor";
  created_at: string;
};
