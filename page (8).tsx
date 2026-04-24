import Link from "next/link";
import { Zap, Eye, TrendingUp, Shield, Star, ArrowRight, CheckCircle2 } from "lucide-react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AIVisoor — Know Where Your Brand Stands in AI Answers",
  description: "Track your AI visibility across ChatGPT, Claude, and Gemini. Get scores, competitor insights, and actionable recommendations.",
};

const FEATURES = [
  {
    icon: Eye,
    title: "AI Visibility Score",
    desc: "See exactly how often your brand appears when people ask ChatGPT, Claude, or Perplexity about topics in your niche.",
    color: "bg-violet-500/10 text-violet-400",
  },
  {
    icon: TrendingUp,
    title: "Competitor Intelligence",
    desc: "Discover which competitors dominate AI answers in your space — and get a clear plan to outrank them.",
    color: "bg-blue-500/10 text-blue-400",
  },
  {
    icon: Shield,
    title: "Authority Score",
    desc: "Measure how authoritative AI models perceive your brand, and get specific content strategies to improve.",
    color: "bg-emerald-500/10 text-emerald-400",
  },
  {
    icon: Star,
    title: "Actionable Reports",
    desc: "Every report ends with prioritized, specific actions. No fluff — just what to do next.",
    color: "bg-amber-500/10 text-amber-400",
  },
];

const PLANS = [
  { name: "Free", price: "$0", features: ["1 report/month", "Basic scores", "Top 5 competitors"], cta: "Start Free", href: "/register", highlight: false },
  { name: "Pro", price: "$79", period: "/month", features: ["50 reports/month", "API access", "Competitor alerts", "Priority support"], cta: "Start 7-day trial", href: "/register", highlight: true },
  { name: "Agency", price: "$199", period: "/month", features: ["Unlimited reports", "White-label", "5 team seats", "Dedicated support"], cta: "Contact Sales", href: "mailto:hello@aivisoor.com", highlight: false },
];

const TESTIMONIALS = [
  {
    text: "After 3 months of using AIVisoor's recommendations, we went from invisible in AI results to being mentioned in 68% of relevant queries.",
    author: "Marketing Director",
    company: "B2B SaaS company",
    score: 68,
  },
  {
    text: "We didn't even know AI visibility was a thing until AIVisoor showed us our competitor was dominating ChatGPT answers while we had zero presence.",
    author: "Head of Growth",
    company: "E-commerce brand",
    score: 42,
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Nav */}
      <nav className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-violet-600 rounded-lg flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-white text-lg">AIVisoor</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-gray-400 hover:text-white text-sm transition-colors">
              Sign in
            </Link>
            <Link href="/register" className="btn-primary text-sm">
              Start Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 py-24 text-center">
        <div className="inline-flex items-center gap-2 bg-violet-600/10 border border-violet-600/30 rounded-full px-4 py-1.5 text-sm text-violet-300 mb-8">
          <Zap className="w-3.5 h-3.5" />
          AI Visibility Analytics Platform
        </div>
        <h1 className="text-5xl sm:text-6xl font-bold text-white mb-6 leading-tight">
          Is your brand{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-blue-400">
            invisible
          </span>
          {" "}in AI answers?
        </h1>
        <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          Millions of people ask ChatGPT, Claude, and Gemini about products every day.
          AIVisoor shows you exactly where you stand — and how to dominate AI results.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/register" className="btn-primary text-base px-8 py-3 flex items-center gap-2 justify-center">
            Analyze Your Brand Free
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link href="#features" className="btn-secondary text-base px-8 py-3 justify-center">
            See How It Works
          </Link>
        </div>
        <p className="text-gray-500 text-sm mt-4">No credit card required · 1 free report/month</p>
      </section>

      {/* Social proof bar */}
      <section className="border-y border-gray-800 py-6 bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-6 flex flex-wrap items-center justify-center gap-8 text-center">
          {[
            { value: "10K+", label: "Reports Generated" },
            { value: "3 AIs", label: "Analyzed (GPT, Claude, Perplexity)" },
            { value: "4 Scores", label: "Per Report" },
            { value: "$0", label: "To Start" },
          ].map(({ value, label }) => (
            <div key={label}>
              <p className="text-2xl font-bold text-white">{value}</p>
              <p className="text-gray-400 text-sm">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-white mb-4">Everything you need to win in the AI era</h2>
          <p className="text-gray-400 max-w-xl mx-auto">
            Traditional SEO is no longer enough. AIVisoor tracks where your brand stands in the new search — AI answers.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {FEATURES.map(({ icon: Icon, title, desc, color }) => (
            <div key={title} className="card hover:border-gray-700 transition-colors">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-4 ${color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-white mb-2">{title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Testimonials */}
      <section className="bg-gray-900/50 border-y border-gray-800 py-16">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-white text-center mb-10">Results that speak for themselves</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {TESTIMONIALS.map((t, i) => (
              <div key={i} className="card">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 bg-violet-600/20 rounded-full flex items-center justify-center">
                    <span className="text-violet-400 font-bold text-lg">{t.score}</span>
                  </div>
                  <div>
                    <p className="text-white font-medium">AI Visibility Score</p>
                    <p className="text-gray-400 text-xs">after using AIVisoor</p>
                  </div>
                </div>
                <p className="text-gray-300 text-sm leading-relaxed mb-4 italic">"{t.text}"</p>
                <div className="text-gray-500 text-xs">
                  — {t.author}, {t.company}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-white mb-4">Simple, transparent pricing</h2>
          <p className="text-gray-400">Start free. Upgrade when you need more.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          {PLANS.map((plan) => (
            <div key={plan.name} className={`card flex flex-col border-2 ${plan.highlight ? "border-violet-500 ring-2 ring-violet-500/30" : "border-gray-800"}`}>
              {plan.highlight && (
                <div className="text-center -mt-8 mb-4">
                  <span className="bg-violet-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                    Most Popular
                  </span>
                </div>
              )}
              <h3 className="font-bold text-white text-lg mb-1">{plan.name}</h3>
              <div className="flex items-baseline gap-1 mb-4">
                <span className="text-3xl font-bold text-white">{plan.price}</span>
                {plan.period && <span className="text-gray-400 text-sm">{plan.period}</span>}
              </div>
              <ul className="space-y-2 flex-1 mb-6">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-gray-300">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link href={plan.href}
                className={`text-center py-2.5 rounded-lg text-sm font-medium transition-colors ${plan.highlight ? "bg-violet-600 hover:bg-violet-500 text-white" : "bg-gray-800 hover:bg-gray-700 text-white"}`}>
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-gradient-to-b from-violet-600/10 to-transparent border-t border-violet-600/20 py-20">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Find out where your brand stands — right now
          </h2>
          <p className="text-gray-400 mb-8">
            Join thousands of brands tracking their AI visibility. First report is free.
          </p>
          <Link href="/register" className="btn-primary text-base px-10 py-3 inline-flex items-center gap-2">
            Get Your Free Report
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-violet-600 rounded flex items-center justify-center">
              <Zap className="w-3 h-3 text-white" />
            </div>
            <span className="text-gray-400 text-sm">AIVisoor © {new Date().getFullYear()}</span>
          </div>
          <div className="flex gap-6 text-sm text-gray-500">
            <Link href="/privacy" className="hover:text-gray-300">Privacy</Link>
            <Link href="/terms" className="hover:text-gray-300">Terms</Link>
            <a href="mailto:hello@aivisoor.com" className="hover:text-gray-300">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
