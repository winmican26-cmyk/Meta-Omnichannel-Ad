import { motion } from "framer-motion";
import {
  ShoppingCart,
  Users,
  UserPlus,
  CreditCard,
  ShoppingBag,
  CheckCircle,
  MousePointerClick,
  Eye,
  Heart,
  Bell,
  FlaskConical,
  Search,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const ICON_MAP: Record<string, LucideIcon> = {
  ShoppingCart,
  Users,
  UserPlus,
  CreditCard,
  ShoppingBag,
  CheckCircle,
  MousePointerClick,
  Eye,
  Heart,
  Bell,
  FlaskConical,
  Search,
};

const COLOR_MAP: Record<string, string> = {
  green: "border-brand-green/30 bg-brand-green/10 text-brand-green",
  blue: "border-brand-blue/30 bg-brand-blue/10 text-brand-blue",
  purple: "border-brand-purple/30 bg-brand-purple/10 text-brand-purple",
  orange: "border-brand-orange/30 bg-brand-orange/10 text-brand-orange",
};

const OBJECTIVES = [
  { value: "DRIVE_SALES", label: "Drive Sales", description: "Optimize for purchase conversions", icon: "ShoppingCart", color: "green" },
  { value: "GET_LEADS", label: "Get Leads", description: "Collect leads and contact info", icon: "Users", color: "blue" },
  { value: "BOOST_REGISTRATIONS", label: "Boost Registrations", description: "Drive sign-ups and account creation", icon: "UserPlus", color: "purple" },
  { value: "ADD_PAYMENT_INFO", label: "Add Payment Info", description: "Encourage saved payment methods", icon: "CreditCard", color: "orange" },
  { value: "ADD_TO_CART", label: "Add to Cart", description: "Get users to add items to cart", icon: "ShoppingBag", color: "green" },
  { value: "COMPLETE_CHECKOUT", label: "Complete Checkout", description: "Drive completed checkouts", icon: "CheckCircle", color: "blue" },
  { value: "DRIVE_TRAFFIC", label: "Drive Traffic", description: "Send traffic to your website or app", icon: "MousePointerClick", color: "purple" },
  { value: "CONTENT_VIEWS", label: "Content Views", description: "Boost content or product page views", icon: "Eye", color: "orange" },
  { value: "ADD_TO_WISHLIST", label: "Add to Wishlist", description: "Encourage users to save items", icon: "Heart", color: "green" },
  { value: "DRIVE_SUBSCRIPTIONS", label: "Drive Subscriptions", description: "Grow recurring subscriptions", icon: "Bell", color: "blue" },
  { value: "START_FREE_TRIAL", label: "Start Free Trial", description: "Promote free trial starts", icon: "FlaskConical", color: "purple" },
  { value: "SEARCH_RETARGETING", label: "Search Retargeting", description: "Retarget users based on search behavior", icon: "Search", color: "orange" },
];

interface StepObjectiveProps {
  data: Record<string, unknown>;
  onChange: (data: Record<string, unknown>) => void;
}

export function StepObjective({ data, onChange }: StepObjectiveProps) {
  const selected = (data?.objective as string) || "";

  const handleSelect = (value: string) => {
    const obj = OBJECTIVES.find((o) => o.value === value);
    onChange({
      objective: value,
      label: obj?.label || value,
    });
  };

  return (
    <div className="space-y-4">
      <div className="mb-2">
        <h3 className="text-lg font-semibold text-text-primary">What's your marketing objective?</h3>
        <p className="text-sm text-text-muted mt-1">
          Choose the goal that best matches what you want to achieve.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {OBJECTIVES.map((obj) => {
          const Icon = ICON_MAP[obj.icon] || ShoppingCart;
          const isSelected = selected === obj.value;
          const colorClasses = COLOR_MAP[obj.color] || COLOR_MAP.blue;

          return (
            <motion.button
              key={obj.value}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleSelect(obj.value)}
              className={`relative text-left p-4 rounded-xl border transition-all duration-200 ${
                isSelected
                  ? `border-brand-blue bg-brand-blue/5 ring-1 ring-brand-blue/30`
                  : "border-surface-border bg-surface-card hover:border-surface-elevated hover:bg-surface-hover"
              }`}
            >
              {isSelected && (
                <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-brand-blue flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}

              <div className={`w-10 h-10 rounded-lg ${colorClasses} flex items-center justify-center mb-3`}>
                <Icon size={20} />
              </div>

              <h4 className="font-semibold text-sm text-text-primary">{obj.label}</h4>
              <p className="text-xs text-text-muted mt-1 leading-relaxed">{obj.description}</p>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
