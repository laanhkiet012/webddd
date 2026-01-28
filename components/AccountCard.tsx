import React from 'react';
import { GolikeAccount } from '../types';
import { Instagram, Lock, Globe, AlertOctagon, Loader2 } from 'lucide-react';

interface AccountCardProps {
  account: GolikeAccount;
  onCookieChange: (id: string, value: string) => void;
  isRunning: boolean;
}

const AccountCard: React.FC<AccountCardProps> = ({ account, onCookieChange, isRunning }) => {
  const isDie = account.status === 'die';
  const isWaiting = account.status === 'waiting';

  return (
    <div className={`border rounded-md p-4 flex flex-col gap-3 relative overflow-hidden transition-all ${isDie ? 'bg-red-950/30 border-red-800 opacity-75' : 'bg-gray-800 border-gray-700 hover:border-cyan-500/50'}`}>
      
      {/* Platform Badge */}
      <div className={`absolute top-0 right-0 p-2 rounded-bl-lg ${account.platform === 'instagram' ? 'bg-pink-600' : 'bg-red-600'} text-white shadow-lg z-10`}>
        {account.platform === 'instagram' ? <Instagram size={14} /> : <Globe size={14} />}
      </div>

      <div className="flex flex-col">
        <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400 uppercase tracking-wider">Username</span>
            {isDie && <span className="text-[10px] bg-red-600 text-white px-1 rounded font-bold">DIE</span>}
        </div>
        <span className={`text-md font-bold truncate pr-8 ${isDie ? 'text-red-400 line-through' : 'text-white'}`}>
            {account.username}
        </span>
        <div className="flex justify-between items-end">
            <span className="text-xs text-gray-500">ID: {account.id}</span>
            <span className={`text-[10px] ${isWaiting ? 'text-yellow-400 animate-pulse' : 'text-cyan-400'}`}>
                {account.lastMessage || account.status}
            </span>
        </div>
      </div>

      <div className="mt-2">
        <label className="text-xs text-cyan-400 mb-1 flex items-center gap-1 font-semibold">
          <Lock size={10} />
          {account.platform === 'instagram' ? 'IG SessionID' : 'Pin Auth'}
        </label>
        <input
          disabled={isRunning || isDie}
          value={account.cookie}
          onChange={(e) => onCookieChange(account.id, e.target.value)}
          placeholder={account.platform === 'instagram' ? "sessionid=..." : "_auth=..."}
          className={`w-full bg-gray-900 border ${account.cookie ? 'border-green-600/30' : 'border-red-900/30'} rounded p-2 text-xs text-gray-300 focus:outline-none focus:border-cyan-500 h-8 transition-colors`}
        />
      </div>

      {isRunning && !isDie && (
        <div className="absolute bottom-0 left-0 w-full h-1 bg-gray-700">
            <div className={`h-full w-full ${isWaiting ? 'bg-yellow-500/50' : 'bg-cyan-500 animate-pulse'}`}></div>
        </div>
      )}
    </div>
  );
};

export default AccountCard;