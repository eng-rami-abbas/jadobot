import { useEffect } from 'react';
import { X } from 'lucide-react';
import { useApp } from '../../contexts/GlobalContext';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  maxWidth?: string;
}

export default function Modal({ isOpen, onClose, title, children, maxWidth = 'max-w-md' }: ModalProps) {
  const { theme } = useApp();
  const isDark = theme === 'dark';

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    if (isOpen) document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className={`relative w-full ${maxWidth} rounded-2xl shadow-2xl border overflow-hidden
        ${isDark ? 'bg-slate-900 border-slate-700/50' : 'bg-white border-slate-200'}
      `}>
        <div className={`flex items-center justify-between px-5 py-4 border-b ${isDark ? 'border-slate-700/50' : 'border-slate-100'}`}>
          <h3 className={`font-semibold ${isDark ? 'text-white' : 'text-slate-800'}`}>{title}</h3>
          <button
            onClick={onClose}
            className={`p-1.5 rounded-lg transition-colors ${isDark ? 'text-slate-400 hover:text-white hover:bg-slate-700' : 'text-slate-400 hover:bg-slate-100'}`}
          >
            <X size={16} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
