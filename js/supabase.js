/**
 * JADO BOT - Supabase Integration
 */

class SupabaseManager {
    constructor() {
        this.supabaseUrl = 'https://kpnxtvargeajpxgswdso.supabase.co';
        this.supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtwbnh0dmFyZ2VhanB4Z3N3ZHNvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1MTM1NDgsImV4cCI6MjA5MjA4OTU0OH0.nLWI13zA_60KixjgE-ErieCuaSg3D756zRW_FqwOh-g';
        this.supabase = null;
        this.initialized = false;
        this.demoMode = true;
    }

    async init() {
        try {
            if (typeof supabase === 'undefined' || !supabase.createClient) {
                console.warn('Supabase library not loaded');
                return false;
            }

            // Check if credentials are set
            if (this.supabaseUrl.includes('your-project')) {
                console.warn('Supabase credentials not configured, using demo mode');
                return false;
            }

            this.supabase = supabase.createClient(this.supabaseUrl, this.supabaseKey);
            this.initialized = true;
            this.demoMode = false;
            console.log('SupabaseManager initialized');
            return true;
        } catch (error) {
            console.error('Supabase init error:', error);
            return false;
        }
    }

    async hasDeposit(userId) {
        if (this.demoMode) return true;
        try {
            const { data, error } = await this.supabase
                .from('deposits').select('id').eq('user_id', userId).limit(1);
            if (error) throw error;
            return data && data.length > 0;
        } catch (error) {
            console.error('hasDeposit error:', error);
            return true;
        }
    }

    async getBalance(userId) {
        if (this.demoMode) return 0;
        try {
            const { data, error } = await this.supabase
                .from('balance').select('amount').eq('user_id', userId).single();
            if (error) throw error;
            return data ? data.amount : 0;
        } catch (error) {
            return 0;
        }
    }

    async hasSpunToday(userId) {
        if (this.demoMode) return false;
        try {
            const today = new Date().toISOString().split('T')[0];
            const { data, error } = await this.supabase
                .from('spins').select('id').eq('user_id', userId).eq('spin_date', today).limit(1);
            if (error) throw error;
            return data && data.length > 0;
        } catch (error) {
            return false;
        }
    }

    async getFreeSpins(userId) {
        if (this.demoMode) return 0;
        try {
            const { data, error } = await this.supabase
                .from('free_spins').select('remaining').eq('user_id', userId).single();
            if (error) throw error;
            return data ? data.remaining : 0;
        } catch (error) {
            return 0;
        }
    }

    async getTotalSpins(userId) {
        if (this.demoMode) return 1;
        const hasDaily = !(await this.hasSpunToday(userId));
        const freeSpins = await this.getFreeSpins(userId);
        return (hasDaily ? 1 : 0) + freeSpins;
    }

    async recordSpin(userId) {
        if (this.demoMode) return true;
        try {
            const today = new Date().toISOString().split('T')[0];
            const { error } = await this.supabase
                .from('spins').insert([{ user_id: userId, spin_date: today }]);
            if (error) throw error;
            return true;
        } catch (error) {
            return false;
        }
    }

    async recordResult(userId, prize) {
        if (this.demoMode) return true;
        try {
            const { error } = await this.supabase
                .from('spin_results').insert([{ user_id: userId, prize: prize }]);
            if (error) throw error;
            return true;
        } catch (error) {
            return false;
        }
    }

    async getSpinResult(userId) {
        if (this.demoMode) {
            return this._fallbackSpinResult(userId);
        }

        try {
            // Try Edge Function first
            const { data, error } = await this.supabase
                .rpc('get_spin_result', { p_user_id: userId });

            if (error) throw error;
            return data;
        } catch (error) {
            console.warn('RPC failed, using fallback:', error);
            return this._fallbackSpinResult(userId);
        }
    }

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

        const random = Math.random() * 100;
        let cumulative = 0;
        for (const prize of prizes) {
            cumulative += prize.weight;
            if (random <= cumulative) return prize.name;
        }
        return prizes[0].name;
    }
}

window.supabaseManager = new SupabaseManager();
