import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { headers } from "next/headers";
import { Providers } from "@/components/providers";
import "leaflet/dist/leaflet.css";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto")?.split(",")[0] ?? (host.startsWith("localhost") ? "http" : "https");
  const origin = `${protocol}://${host}`;
  const imageUrl = new URL("/og.png", origin).toString();
  const title = "Magic Trip Planner — Sri Lanka itineraries made simple";
  const description = "Plan a practical Sri Lanka itinerary with places, stays, daily routes, and a clear LKR budget.";

  return {
    metadataBase: new URL(origin),
    title: { default: title, template: "%s · Magic Trip Planner" },
    description,
    icons: { icon: "/logo.png", apple: "/logo.png" },
    openGraph: {
      title,
      description,
      type: "website",
      url: origin,
      siteName: "Magic Trip Planner",
      images: [{ url: imageUrl, width: 1536, height: 1024, alt: "Less planning. More going. Magic Trip Planner Sri Lanka." }],
    },
    twitter: { card: "summary_large_image", title, description, images: [imageUrl] },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full bg-[#f8f7f2] text-[#173e34]">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
