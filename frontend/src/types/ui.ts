
import type { ReactNode } from "react";

export type JsonLike = Record<string, unknown>;
export type DataTableRow = Record<string, unknown>;
export type DataTableColumn<T extends DataTableRow> = keyof T & string;

export interface LoadingState {
  isLoading: boolean;
  error?: string;
}

export interface DataTableProps<T extends DataTableRow> {
  data: T[];
  columns?: DataTableColumn<T>[];
  isLoading?: boolean;
  maxRows?: number;
  enableFilter?: boolean;
  enablePagination?: boolean;
  pageSize?: number;
}

export interface ConfidenceBadgeProps {
  level: "high" | "medium" | "low";
  showLabel?: boolean;
}

export interface ButtonProps {
  variant?: "primary" | "secondary" | "danger";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  loading?: boolean;
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}

export interface InsightCardProps {
  icon: ReactNode;
  title: string;
  value: string | number;
  subtitle?: string;
  color?: "blue" | "green" | "yellow" | "red";
}

export interface HeaderProps {
  onMenuClick: () => void;
  sidebarOpen: boolean;
}

export interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export interface ResultMetadataProps {
  metadata: JsonLike;
}

export interface ResultsContainerProps {
  message: JsonLike;
}

export interface ClarificationDialogProps {
  message: JsonLike;
  originalQuery: string;
}

export interface Suggestion {
  id: number;
  name: string;
  schema: string;
}

export interface SuggestionCardProps {
  suggestion: Suggestion;
  selected: boolean;
  onSelect: () => void;
  disabled?: boolean;
}

export interface QueryHistoryItem {
  id: string;
  query: string;
  timestamp: Date;
}

export interface QueryHistoryProps {
  queries?: QueryHistoryItem[];
}