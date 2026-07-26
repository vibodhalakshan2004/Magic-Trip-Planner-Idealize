import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "MagicTripPlanner",
    short_name: "MagicTrip",
    description: "Sri Lanka itinerary, route, accommodation, and budget planner.",
    start_url: "/",
    display: "standalone",
    background_color: "#f8fafc",
    theme_color: "#059669",
    icons: [{ src: "/logo.png", sizes: "any", type: "image/png" }],
  };
}
