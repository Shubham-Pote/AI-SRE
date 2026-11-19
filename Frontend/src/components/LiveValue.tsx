import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";

// Animate real observations without delaying or replacing their accessible value.
export function LiveValue({ value }: { value: string }) {
  const node = useRef<HTMLSpanElement>(null);
  const previous = useRef<number | null>(null);
  useGSAP(() => {
    const match = value.match(/^(\d+(?:\.\d+)?)(.*)$/);
    if (!match || !node.current || match[2]?.includes("/")) return;
    const next = Number(match[1]);
    const decimals = match[1]?.split(".")[1]?.length ?? 0;
    const from = previous.current ?? next;
    previous.current = next;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const state = { number: from };
    gsap.to(state, { number: next, duration: .65, ease: "power2.out", onUpdate: () => {
      if (node.current) node.current.textContent = state.number.toFixed(decimals) + (match[2] ?? "");
    } });
  }, { dependencies: [value], revertOnUpdate: true });
  return <span aria-label={value}><span ref={node} aria-hidden="true">{value}</span></span>;
}
