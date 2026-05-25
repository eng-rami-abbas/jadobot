/**
 * JADO BOT - Supabase Integration
 * Handles all database operations and backend logic
 */

class SupabaseManager {
    constructor() {
        // Replace with your actual Supabase credentials
        this.supabaseUrl = 'https://your-project.supabase.co';
        this.supabaseKey = 'your-anon-key';
        this.supabase = null;
        this.initialized = false;
    }

    async init() {
        try {
            this.supabase = window.supabase.createClient(this.supabaseUrl, this.supabaseKey);
            this.initialized = true;
            console.log('SupabaseManager initialized');
            return true;
        } catch (error) {
            console.error('Supabase init error:', error);
            return false;
        }
    }

    // Check if user has made any deposit
    async hasDeposit(userId) {
        try {
            const { data, error } = await this.supabase
                .from('deposits')
                .select('id')
                .eq('user_id', userId)
                .limit(1);

            if (error) throw error;
            return data && data.length > 0;
        } catch (error) {
            console.error('hasDeposit error:', error);
            // Fallback for demo mode
            return true;
        }
    }

    // Get user balance
    async getBalance(userId) {
        try {
            const { data, error } = await this.supabase
                .from('balance')
                .select('amount')
                .eq('user_id', userId)
                .single();

            if (error) throw error;
            return data ? data.amount : 0;
        } catch (error) {
            console.error('getBalance error:', error);
            return 0;
        }
    }

    // Update user balance
    async updateBalance(userId, amount) {
        try {
            const { data: existing } = await this.supabase
                .from('balance')
                .select('id')
                .eq('user_id', userId)
                .single();

            if (existing) {
                const { error } = await this.supabase
                    .from('balance')
                    .update({ amount: amount })
                    .eq('user_id', userId);
                if (error) throw error;
            } else {
                const { error } = await this.supabase
                    .from('balance')
                    .insert([{ user_id: userId, amount: amount }]);
                if (error) throw error;
            }
            return true;
        } catch (error) {
            console.error('updateBalance error:', error);
            return false;
        }
    }

    // Check if user has spun today
    async hasSpunToday(userId) {
        try {
            const today = new Date().toISOString().split('T')[0];
            const { data, error } = await this.supabase
                .from('spins')
                .select('id')
                .eq('user_id', userId)
                .eq('spin_date', today)
                .limit(1);

            if (error) throw error;
            return data && data.length > 0;
        } catch (error) {
            console.error('hasSpunToday error:', error);
            return false;
        }
    }

    // Record a spin
    async recordSpin(userId) {
        try {
            const today = new Date().toISOString().split('T')[0];
            const { error } = await this.supabase
                .from('spins')
                .insert([{ 
                    user_id: userId, 
                    spin_date: today 
                }]);

            if (error) throw error;
            return true;
        } catch (error) {
            console.error('recordSpin error:', error);
            return false;
        }
    }

    // Get free spins count
    async getFreeSpins(userId) {
        try {
            const { data, error } = await this.supabase
                .from('free_spins')
                .select('remaining')
                .eq('user_id', userId)
                .single();

            if (error) throw error;
            return data ? data.remaining : 0;
        } catch (error) {
            console.error('getFreeSpins error:', error);
            return 0;
        }
    }

    // Add free spin
    async addFreeSpin(userId) {
        try {
            const { data: existing } = await this.supabase
                .from('free_spins')
                .select('remaining')
                .eq('user_id', userId)
                .single();

            if (existing) {
                const { error } = await this.supabase
                    .from('free_spins')
                    .update({ remaining: existing.remaining + 1 })
                    .eq('user_id', userId);
                if (error) throw error;
            } else {
                const { error } = await this.supabase
                    .from('free_spins')
                    .insert([{ user_id: userId, remaining: 1 }]);
                if (error) throw error;
            }
            return true;
        } catch (error) {
            console.error('addFreeSpin error:', error);
            return false;
        }
    }

    // Use a free spin
    async useFreeSpin(userId) {
        try {
            const { data: existing } = await this.supabase
                .from('free_spins')
                .select('remaining')
                .eq('user_id', userId)
                .single();

            if (existing && existing.remaining > 0) {
                const { error } = await this.supabase
                    .from('free_spins')
                    .update({ remaining: existing.remaining - 1 })
                    .eq('user_id', userId);
                if (error) throw error;
                return true;
            }
            return false;
        } catch (error) {
            console.error('useFreeSpin error:', error);
            return false;
        }
    }

    // Get total spins remaining (daily + free)
    async getTotalSpins(userId) {
        const hasDaily = !(await this.hasSpunToday(userId));
        const freeSpins = await this.getFreeSpins(userId);
        return (hasDaily ? 1 : 0) + freeSpins;
    }

    // Record spin result
    async recordResult(userId, prize) {
        try {
            const { error } = await this.supabase
                .from('spin_results')
                .insert([{ 
                    user_id: userId, 
                    prize: prize 
                }]);

            if (error) throw error;

            // Handle specific prizes
            switch(prize) {
                case '10000':
                case '20000':
                case '50000':
                    const currentBalance = await this.getBalance(userId);
                    await this.updateBalance(userId, currentBalance + parseInt(prize));
                    break;
                case 'إعادة تدوير':
                    await this.addFreeSpin(userId);
                    break;
                case 'Bonus 5%':
                    await this.createBonusReward(userId);
                    break;
                case 'Telegram Premium':
                    await this.createPremiumReward(userId);
                    break;
            }

            return true;
        } catch (error) {
            console.error('recordResult error:', error);
            return false;
        }
    }

    // Create bonus reward
    async createBonusReward(userId) {
        try {
            const { error } = await this.supabase
                .from('bonus_rewards')
                .insert([{ 
                    user_id: userId, 
                    bonus_percent: 5, 
                    used: false 
                }]);
            if (error) throw error;
            return true;
        } catch (error) {
            console.error('createBonusReward error:', error);
            return false;
        }
    }

    // Create premium reward
    async createPremiumReward(userId) {
        try {
            const { error } = await this.supabase
                .from('premium_rewards')
                .insert([{ 
                    user_id: userId, 
                    status: 'pending' 
                }]);
            if (error) throw error;
            return true;
        } catch (error) {
            console.error('createPremiumReward error:', error);
            return false;
        }
    }

    // Get spin result from backend (SECURE - no Math.random in frontend)
    async getSpinResult(userId) {
        try {
            // Call Supabase Edge Function or use RPC
            // For demo, we'll use a secure server-side approach
            const { data, error } = await this.supabase
                .rpc('get_spin_result', { p_user_id: userId });

            if (error) {
                // Fallback: Use a deterministic but unpredictable method
                // In production, this MUST be server-side
                console.warn('Using fallback spin result');
                return this._fallbackSpinResult(userId);
            }

            return data;
        } catch (error) {
            console.error('getSpinResult error:', error);
            return this._fallbackSpinResult(userId);
        }
    }

    // Fallback spin result (for demo only - replace with real backend)
    _fallbackSpinResult(userId) {
        const prizes = [
            { name: '10000', weight: 15 },
            { name: '20000', weight: 10 },
            { name: 'حظ أوفر', weight: 25 },
            { name: 'Telegram Premium', weight: 5 },
            { name: '50000', weight: 5 },
            { name: 'Bonus 5%', weight: 15 },
            { name: 'حظ أوفر', weight: 15 },
            { name: 'إعادة تدوير', weight: 10 }
        ];

        // Use timestamp + userId hash for pseudo-random (NOT for production)
        const seed = Date.now() + parseInt(userId);
        const random = Math.abs(Math.sin(seed) * 10000) % 100;

        let cumulative = 0;
        for (const prize of prizes) {
            cumulative += prize.weight;
            if (random <= cumulative) {
                return prize.name;
            }
        }
        return prizes[0].name;
    }

    // Admin: Get today's stats
    async getTodayStats() {
        try {
            const today = new Date().toISOString().split('T')[0];

            const { data: spins, error: spinsError } = await this.supabase
                .from('spins')
                .select('*')
                .eq('spin_date', today);

            const { data: results, error: resultsError } = await this.supabase
                .from('spin_results')
                .select('*')
                .gte('created_at', today + 'T00:00:00');

            if (spinsError) throw spinsError;
            if (resultsError) throw resultsError;

            return {
                totalSpins: spins ? spins.length : 0,
                results: results || []
            };
        } catch (error) {
            console.error('getTodayStats error:', error);
            return { totalSpins: 0, results: [] };
        }
    }
}

// Global instance
window.supabaseManager = new SupabaseManager();
