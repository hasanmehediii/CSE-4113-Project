import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import "./landing-enhancements.css";
import { Providers } from "@/components/Providers";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: { default: "DubsiBhai — A better Dhaka, together", template: "%s | DubsiBhai" },
  description: "Urban waterlogging and drainage management for Dhaka.",
  icons: { icon: "/logo.png" },
  referrer: "no-referrer",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: `try{var d=document.documentElement;var t=localStorage.getItem('dubsi-theme');d.dataset.theme=t==='dark'||(!t&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light';d.lang=localStorage.getItem('dubsi-language')==='bn'?'bn':'en'}catch(e){}` }} /></head>
      <body><Providers><Navbar />{children}<Footer /></Providers></body>
    </html>
  );
}
