/** Display-only segment layout (must match server roulette_config.py order). */
export const SEGMENTS = [
  { index: 0, type: 'cash', label: '10,000', labelAr: '10,000 ل.س', icon: '💵', color: '#8b1530', colorEnd: '#5c0a1f' },
  { index: 1, type: 'cash', label: '20,000', labelAr: '20,000 ل.س', icon: '💵', color: '#2d1f5e', colorEnd: '#1a1240' },
  { index: 2, type: 'none', label: 'حظ أوفر', labelAr: 'حظ أوفر', icon: '🍀', color: '#8b1530', colorEnd: '#5c0a1f' },
  { index: 3, type: 'premium', label: 'Premium', labelAr: 'تيليجرام بريميوم', icon: '✈️', color: '#2d1f5e', colorEnd: '#1a1240' },
  { index: 4, type: 'cash', label: '50,000', labelAr: '50,000 ل.س', icon: '💵', color: '#8b1530', colorEnd: '#5c0a1f' },
  { index: 5, type: 'bonus', label: '5%', labelAr: 'بونص 5%', icon: '🎁', color: '#2d1f5e', colorEnd: '#1a1240' },
  { index: 6, type: 'none', label: 'حظ أوفر', labelAr: 'حظ أوفر', icon: '🍀', color: '#8b1530', colorEnd: '#5c0a1f' },
  { index: 7, type: 'respin', label: 'Respin', labelAr: 'إعادة تدوير', icon: '🔄', color: '#2d1f5e', colorEnd: '#1a1240' },
];

export const SEGMENT_ARC = 360 / SEGMENTS.length;
