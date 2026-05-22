// Cashier Service - إدارة الكاشير واللاعبين
export interface CashierPlayer {
  id: string;
  telegram_id: number;
  username: string;
  first_name: string;
  balance_syp: number;
  balance_usd: number;
  is_active: boolean;
  last_active: string;
  created_at: string;
  total_deposits: number;
  total_withdrawals: number;
  operations_count: number;
  is_blocked: boolean;
}

export interface AgentWallet {
  id: string;
  agent_id: string;
  wallet_name: string;
  wallet_address: string;
  currency: 'SYP' | 'USD';
  balance: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CashierTransaction {
  id: string;
  player_id: string;
  agent_id: string;
  type: 'deposit' | 'withdrawal' | 'transfer';
  amount: number;
  currency: 'SYP' | 'USD';
  status: 'pending' | 'completed' | 'rejected';
  method: string;
  reference: string;
  notes: string;
  created_at: string;
  processed_at?: string;
}

export interface CashierStats {
  totalPlayers: number;
  activePlayers: number;
  totalBalanceSYP: number;
  totalBalanceUSD: number;
  todayTransactions: number;
  todayVolume: number;
  pendingTransactions: number;
}

export class CashierService {
  private static instance: CashierService;
  private baseURL: string;
  private apiKey: string;

  private constructor() {
    this.baseURL = process.env.REACT_APP_CASHIER_API_URL || 'https://api.cashier.example.com';
    this.apiKey = process.env.REACT_APP_CASHIER_API_KEY || '';
  }

  static getInstance(): CashierService {
    if (!CashierService.instance) {
      CashierService.instance = new CashierService();
    }
    return CashierService.instance;
  }

  // 🎮 الحصول على بيانات اللاعبين
  async getPlayers(page = 1, limit = 50, search = '', status = 'all'): Promise<{
    players: CashierPlayer[];
    total: number;
    page: number;
  }> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
        search,
        status,
      });

      const response = await fetch(`${this.baseURL}/players?${params}`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch players: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[CashierService] Error fetching players:', error);
      throw error;
    }
  }

  // 💰 الحصول على محافظ الوكلاء
  async getAgentWallets(agentId: string): Promise<AgentWallet[]> {
    try {
      const response = await fetch(`${this.baseURL}/agents/${agentId}/wallets`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch agent wallets: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[CashierService] Error fetching agent wallets:', error);
      throw error;
    }
  }

  // 📊 الحصول على معاملات الكاشير
  async getTransactions(page = 1, limit = 50, type = 'all', status = 'all'): Promise<{
    transactions: CashierTransaction[];
    total: number;
    page: number;
  }> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
        type,
        status,
      });

      const response = await fetch(`${this.baseURL}/transactions?${params}`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch transactions: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[CashierService] Error fetching transactions:', error);
      throw error;
    }
  }

  // 📈 الحصول على إحصائيات الكاشير
  async getStats(): Promise<CashierStats> {
    try {
      const response = await fetch(`${this.baseURL}/stats`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch stats: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[CashierService] Error fetching stats:', error);
      throw error;
    }
  }

  // 💸 إيداع للاعب
  async depositToPlayer(playerId: string, amount: number, currency: 'SYP' | 'USD', method: string, notes = ''): Promise<CashierTransaction> {
    try {
      const response = await fetch(`${this.baseURL}/transactions/deposit`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          player_id: playerId,
          amount,
          currency,
          method,
          notes,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create deposit: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[CashierService] Error creating deposit:', error);
      throw error;
    }
  }

  // 🏧 سحب من لاعب
  async withdrawFromPlayer(playerId: string, amount: number, currency: 'SYP' | 'USD', method: string, notes = ''): Promise<CashierTransaction> {
    try {
      const response = await fetch(`${this.baseURL}/transactions/withdraw`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          player_id: playerId,
          amount,
          currency,
          method,
          notes,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create withdrawal: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[CashierService] Error creating withdrawal:', error);
      throw error;
    }
  }

  // ✅ معالجة معاملة
  async processTransaction(transactionId: string, status: 'completed' | 'rejected', notes = ''): Promise<CashierTransaction> {
    try {
      const response = await fetch(`${this.baseURL}/transactions/${transactionId}/process`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          status,
          notes,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to process transaction: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[CashierService] Error processing transaction:', error);
      throw error;
    }
  }

  // 🔄 تحديث رصيد اللاعب
  async updatePlayerBalance(playerId: string, balanceSYP: number, balanceUSD: number): Promise<CashierPlayer> {
    try {
      const response = await fetch(`${this.baseURL}/players/${playerId}/balance`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          balance_syp: balanceSYP,
          balance_usd: balanceUSD,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to update player balance: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[CashierService] Error updating player balance:', error);
      throw error;
    }
  }

  // 🚫 حظر/إلغاء حظر لاعب
  async togglePlayerBlock(playerId: string, isBlocked: boolean): Promise<CashierPlayer> {
    try {
      const response = await fetch(`${this.baseURL}/players/${playerId}/block`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          is_blocked: isBlocked,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to toggle player block: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[CashierService] Error toggling player block:', error);
      throw error;
    }
  }

  // 📊 الحصول على تقرير المعاملات
  async getTransactionReport(startDate: string, endDate: string, type = 'all'): Promise<{
    total_transactions: number;
    total_volume: number;
    successful_transactions: number;
    failed_transactions: number;
    pending_transactions: number;
    breakdown_by_type: Record<string, number>;
    breakdown_by_currency: Record<string, number>;
    daily_stats: Array<{
      date: string;
      transactions: number;
      volume: number;
    }>;
  }> {
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        type,
      });

      const response = await fetch(`${this.baseURL}/reports/transactions?${params}`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch transaction report: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[CashierService] Error fetching transaction report:', error);
      throw error;
    }
  }
}

export default CashierService.getInstance();
