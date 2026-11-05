import "./globals.css";
import { Shell } from "./shell";

export const metadata = { title: "CareerAssist" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
