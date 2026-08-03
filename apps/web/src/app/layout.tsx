import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Examen de Grado",
  description: "Plataforma inteligente de preparación para el Examen de Grado Oral",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-CL">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
