import './globals.css';

export const metadata = {
  title: 'GPU Optimizer',
  description: 'Optimize GPU workloads with ease',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head />
      <body>{children}</body>
    </html>
  );
}
