import { Capabilities } from "@/features/landing/components/Capabilities";
import { CatCardShowcase } from "@/features/landing/components/CatCardShowcase";
import { CtaSection } from "@/features/landing/components/CtaSection";
import { Faq } from "@/features/landing/components/Faq";
import { Footer } from "@/features/landing/components/Footer";
import { Hero } from "@/features/landing/components/Hero";
import { HowItWorks } from "@/features/landing/components/HowItWorks";
import { Navbar } from "@/features/landing/components/Navbar";
import { TechStack } from "@/features/landing/components/TechStack";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <Navbar />
      <main className="flex-1">
        <Hero />
        <HowItWorks />
        <Capabilities />
        <CatCardShowcase />
        <TechStack />
        <Faq />
        <CtaSection />
      </main>
      <Footer />
    </div>
  );
}
