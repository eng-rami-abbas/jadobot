-- Add pending wheel bonus percent to wheel_spins (applied on next approved deposit)
ALTER TABLE wheel_spins
  ADD COLUMN IF NOT EXISTS pending_bonus_percent numeric DEFAULT 0;

NOTIFY pgrst, 'reload schema';
