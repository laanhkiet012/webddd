import React from 'react';
import { WorkerStats } from '../types';
import { TrendingUp, CheckCircle, XCircle, Clock, Wallet } from 'lucide-react';

interface StatsBoardProps {
  stats: WorkerStats;
}

const StatItem = ({ label, value, icon, color, subColor }: { label: string, value: string, icon: React.ReactNode, color: string, subColor?: string }) => (
    <div className={`bg-gray-800/50 p-3 rounded border border-gray-700 flex items-center gap-3 relative overflow-hidden`}>
        <div className={`p-2 rounded-full bg-gray-900 ${color} z-10`}>
            {icon}
        </div>
        <div className="z-10">
            <div className="text-xs text-gray-400 uppercase font-semibold">{label}</div>
            <div className="text-lg font-bold text-white font-mono">{value}</div>
        </div>
        {subColor && (
            <div className={`absolute -right-2 -bottom-4 w-16 h-16 rounded-full opacity-10 ${subColor}`}></div>
        )}
    </div>
)

const StatsBoard: React.FC<StatsBoardProps> = ({ stats }) => {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <StatItem 
            label="Số dư tạm tính" 
            value={`${stats.totalMoney.toLocaleString()}đ`} 
            icon={<Wallet size={18} />}
            color="text-yellow-400"
            subColor="bg-yellow-400"
        />
        <StatItem 
            label="Tổng Job đã làm" 
            value={stats.totalJobs.toString()} 
            icon={<CheckCircle size={18} />}
            color="text-green-400"
            subColor="bg-green-400"
        />
        <StatItem 
            label="Chờ duyệt" 
            value={stats.pendingJobs.toString()} 
            icon={<Clock size={18} />}
            color="text-blue-400"
            subColor="bg-blue-400"
        />
        <StatItem 
            label="Làm lỗi / Die" 
            value={stats.fails.toString()} 
            icon={<XCircle size={18} />}
            color="text-red-400"
            subColor="bg-red-400"
        />
    </div>
  );
};

export default StatsBoard;