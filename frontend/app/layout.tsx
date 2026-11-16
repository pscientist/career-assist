import "./globals.css";
import { Shell } from "./shell";

export const metadata = { title: "CareerAssist — Stay afloat in a changing job market" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
