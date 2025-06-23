import "@/styles/globals.css";
import ClientWrapper from "@/components/ClientWrapper";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <title>WorkMatch - Career Progression Made Easy</title>
        <meta name="theme-color" content="#0f172a" />
      </head>
      <body className="bg-background text-text min-h-screen">
        <ClientWrapper>{children}</ClientWrapper>
      </body>
    </html>
  );
}
