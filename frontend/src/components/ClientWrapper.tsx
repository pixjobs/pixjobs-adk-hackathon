"use client";

import { useEffect, useState } from "react";

export default function ClientWrapper({ children }: { children: React.ReactNode }) {
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const updateVH = () => {
      const vh = window.visualViewport?.height || window.innerHeight;
      document.documentElement.style.setProperty("--vh", `${vh * 0.01}px`);
    };

    updateVH();
    window.addEventListener("resize", updateVH);
    setHydrated(true);

    return () => window.removeEventListener("resize", updateVH);
  }, []);

  if (!hydrated) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background text-text">
        <p className="text-lg animate-pulse">Loading…</p>
      </div>
    );
  }

  return <>{children}</>;
}
