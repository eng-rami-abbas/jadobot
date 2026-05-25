/**
 * JADO BOT - Supabase Edge Function
 * Secure spin result generation (runs server-side)
 * 
 * Deploy this to Supabase Edge Functions:
 * supabase functions deploy get-spin-result
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const PRIZES = [
    { name: '10000', weight: 15 },
    { name: '20000', weight: 10 },
    { name: 'حظ أوفر', weight: 25 },
    { name: 'Telegram Premium', weight: 5 },
    { name: '50000', weight: 5 },
    { name: 'Bonus 5%', weight: 15 },
    { name: 'حظ أوفر', weight: 15 },
    { name: 'إعادة تدوير', weight: 10 }
];

Deno.serve(async (req) => {
    // CORS headers
    const headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Content-Type': 'application/json'
    };

    if (req.method === 'OPTIONS') {
        return new Response(null, { headers, status: 204 });
    }

    try {
        const { user_id } = await req.json();

        if (!user_id) {
            return new Response(
                JSON.stringify({ error: 'User ID required' }),
                { headers, status: 400 }
            );
        }

        // Create Supabase client with service role
        const supabase = createClient(
            Deno.env.get('SUPABASE_URL'),
            Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
        );

        // Check if user has deposit
        const { data: deposits } = await supabase
            .from('deposits')
            .select('id')
            .eq('user_id', user_id)
            .limit(1);

        if (!deposits || deposits.length === 0) {
            return new Response(
                JSON.stringify({ error: 'No deposit found' }),
                { headers, status: 403 }
            );
        }

        // Check daily spin limit
        const today = new Date().toISOString().split('T')[0];
        const { data: todaySpins } = await supabase
            .from('spins')
            .select('id')
            .eq('user_id', user_id)
            .eq('spin_date', today)
            .limit(1);

        // Check free spins
        const { data: freeSpins } = await supabase
            .from('free_spins')
            .select('remaining')
            .eq('user_id', user_id)
            .single();

        const hasDailySpin = !todaySpins || todaySpins.length === 0;
        const hasFreeSpins = freeSpins && freeSpins.remaining > 0;

        if (!hasDailySpin && !hasFreeSpins) {
            return new Response(
                JSON.stringify({ error: 'No spins remaining' }),
                { headers, status: 403 }
            );
        }

        // Generate cryptographically secure random result
        const cryptoRandom = () => {
            const array = new Uint32Array(1);
            crypto.getRandomValues(array);
            return array[0] / (0xFFFFFFFF + 1);
        };

        const random = cryptoRandom();
        const totalWeight = PRIZES.reduce((sum, p) => sum + p.weight, 0);
        let cumulative = 0;
        let result = PRIZES[0].name;

        for (const prize of PRIZES) {
            cumulative += prize.weight;
            if (random <= cumulative / totalWeight) {
                result = prize.name;
                break;
            }
        }

        return new Response(
            JSON.stringify({ 
                result,
                random_value: random,
                timestamp: new Date().toISOString()
            }),
            { headers, status: 200 }
        );

    } catch (error) {
        return new Response(
            JSON.stringify({ error: error.message }),
            { headers, status: 500 }
        );
    }
});
