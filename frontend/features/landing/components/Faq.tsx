import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqs = [
  {
    question: "Is the breed prediction medically or scientifically certified?",
    answer:
      "No. Breed classification is a computer vision estimate with a confidence score, not a veterinary or scientific determination. MeowVerse never makes medical or veterinary claims.",
  },
  {
    question: "What's the difference between the 'real' and 'magic' parts of a profile?",
    answer:
      "Breed, fur colors, and similarity are outputs of real computer vision models. Personality, magic power, rarity, and the story are AI-generated for fun and are always labeled as creative content, not predictions.",
  },
  {
    question: "What happens if I don't have an AI provider configured?",
    answer:
      "The core analysis still works. Creative generation (profile, story, wallpapers) gracefully shows an 'AI unavailable' state instead of faking a result.",
  },
  {
    question: "Do I need an account to try it?",
    answer:
      "You can run an analysis without an account. Creating one lets you save results, build a collection, and unlock achievements.",
  },
];

export function Faq() {
  return (
    <section id="faq" className="mx-auto max-w-3xl px-4 py-20 sm:px-6">
      <div className="text-center">
        <h2 className="font-heading text-3xl font-bold tracking-tight sm:text-4xl">
          Frequently asked questions
        </h2>
      </div>

      <Accordion className="mt-10">
        {faqs.map((faq, i) => (
          <AccordionItem key={faq.question} value={`item-${i}`}>
            <AccordionTrigger className="text-left font-heading text-base">
              {faq.question}
            </AccordionTrigger>
            <AccordionContent className="text-muted-foreground">{faq.answer}</AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </section>
  );
}
