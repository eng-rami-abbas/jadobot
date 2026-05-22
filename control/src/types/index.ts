export interface BotUser {
  id: string;
  telegram_id: number;
  username: string;
  first_name: string;
  last_name: string;
  balance_syp: number;
  balance_usd: number;
  is_blocked: boolean;
  total_deposits: number;
  total_withdrawals: number;
  operations_count: number;
  created_at: string;
  last_active: string;
}

export interface Transaction {
  id: string;
  operation_number: number;
  user_id: string | null;
  telegram_id: number;
  username: string;
  type: 'deposit' | 'withdrawal' | 'gift' | 'admin_withdraw';
  amount_usd: number;
  amount_syp: number;
  exchange_rate: number;
  status: 'pending' | 'completed' | 'rejected';
  wallet_name: string;
  wallet_address: string;
  account_number: string;
  method: string;
  fee_amount: number;
  bonus_amount?: number;
  bonus_percentage?: number;
  total_amount?: number;
  notes: string;
  created_at: string;
}

export interface Message {
  id: string;
  user_id: string | null;
  telegram_id: number;
  username: string;
  direction: 'incoming' | 'outgoing';
  content: string;
  is_read: boolean;
  created_at: string;
}

export interface Wallet {
  id: string;
  name: string;
  key: string;
  wallet_number: string;
  address: string;
  title: string;
  image_url: string;
  emoji: string;
  is_active: boolean;
  message_template: string;
  sort_order: number;
  bonus_percentage?: number;
  created_at: string;
  updated_at: string;
}

export interface WithdrawalMethod {
  id: string;
  name: string;
  key: string;
  fee_percentage: number;
  input_label: string;
  is_active: boolean;
  sort_order: number;
}

export interface AppSetting {
  id: string;
  key: string;
  value: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  type: 'deposit' | 'withdrawal' | 'message' | 'events'| 'user' | 'gift-codes' | 'system';
  title: string;
  body: string;
  is_read: boolean;
  data: Record<string, unknown>;
  created_at: string;
}

export interface BotBalance {
  id: string;
  balance_syp: number;
  balance_usd: number;
  updated_at: string;
}

export type Page = 'dashboard' | 'users' | 'messages' | 'events' | 'deposits' | 'withdrawals' | 'wallets' | 'withdrawal-methods' | 'gift-codes' | 'broadcast' | 'settings';
export type Theme = 'dark' | 'light';
export type Language = 'ar' | 'en';
