const stack = [
  "Next.js",
  "TypeScript",
  "Tailwind CSS",
  "FastAPI",
  "PostgreSQL",
  "Redis",
  "PyTorch",
  "OpenCV",
];

export function TechStack() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <p className="text-center text-sm font-medium uppercase tracking-wider text-muted-foreground">
        Built with a real product stack
      </p>
      <ul className="mt-6 flex flex-wrap items-center justify-center gap-3">
        {stack.map((item) => (
          <li
            key={item}
            className="rounded-full border border-border bg-card px-4 py-1.5 text-sm text-muted-foreground"
          >
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
