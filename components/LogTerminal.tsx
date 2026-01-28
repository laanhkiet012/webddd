import React, { useEffect, useRef, useState } from 'react';
import { LogEntry, LogType } from '../types';
import { Terminal, Filter, XCircle, CheckCircle, DollarSign, List } from 'lucide-react';

interface LogTerminalProps {
  logs: LogEntry[];
}

const LogTerminal: React.FC<LogTerminalProps> = ({ logs }) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<'all' | 'money' | 'fail'>('all');

  const filteredLogs = logs.filter(log => {
      if (filter === 'all') return true;
      if (filter === 'money') return log.type === 'money';
      if (filter === 'fail') return log.type === 'fail' || log.type === 'warn';
      return true;
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs, filter]);

  const getIcon = (type: LogType) => {
    switch (type) {
      case 'money': return <DollarSign size={14} className="text-yellow-400" />;
      case 'success': return <CheckCircle size={14} className="text-green-400" />;
      case 'fail': return <XCircle size={14} className="text-red-500" />;
      default: return null;
    }
  };

  const getColor = (type: LogType) => {
    switch (type) {
      case 'money': return 'text-yellow-300 font-bold bg-yellow-900/10';
      case 'success': return 'text-green-400';
      case 'fail': return 'text-red-400 bg-red-900/10';
      case 'warn': return 'text-orange-300';
      default: return 'text-gray-300';
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Terminal size={16} className="text-cyan-400" />
          <span className="text-sm font-semibold text-gray-200 font-mono hidden sm:inline">TERMINAL</span>
        </div>
        
        {/* Filter Controls */}
        <div className="flex items-center gap-2 bg-gray-900 p-1 rounded-lg border border-gray-700">
            <button 
                onClick={() => setFilter('all')}
                className={`px-2 py-0.5 text-[10px] rounded flex items-center gap-1 ${filter === 'all' ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'}`}
            >
                <List size={10} /> ALL
            </button>
            <button 
                onClick={() => setFilter('money')}
                className={`px-2 py-0.5 text-[10px] rounded flex items-center gap-1 ${filter === 'money' ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-800' : 'text-gray-500 hover:text-gray-300'}`}
            >
                <DollarSign size={10} /> $$$
            </button>
            <button 
                onClick={() => setFilter('fail')}
                className={`px-2 py-0.5 text-[10px] rounded flex items-center gap-1 ${filter === 'fail' ? 'bg-red-900/30 text-red-400 border border-red-800' : 'text-gray-500 hover:text-gray-300'}`}
            >
                <XCircle size={10} /> ERRORS
            </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1 bg-gray-950/80">
        {filteredLogs.length === 0 && (
          <div className="text-gray-600 text-center mt-10 italic opacity-50">
            {filter === 'all' ? 'Ready to run...' : 'No logs for this filter yet.'}
          </div>
        )}
        {filteredLogs.map((log) => (
          <div key={log.id} className={`flex items-start gap-2 ${getColor(log.type)} p-0.5 rounded transition-all border-l-2 border-transparent hover:border-gray-600 hover:bg-gray-800/50`}>
            <span className="text-gray-600 min-w-[65px] select-none text-[10px] opacity-70">[{log.timestamp}]</span>
            <span className="text-cyan-600 font-bold min-w-[90px] select-none truncate">[{log.accountName}]</span>
            <span className="mt-0.5">{getIcon(log.type)}</span>
            <span className="break-words flex-1">{log.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default LogTerminal;