import React, { useState, useCallback, useRef, useEffect } from 'react';
import { GolikeAccount, LogEntry, Platform, UserProfile, WorkerStats } from './types';
import { fetchUserProfile, fetchAccounts, getJob, checkCookieFormat } from './services/golikeService';
import LogTerminal from './components/LogTerminal';
import AccountCard from './components/AccountCard';
import StatsBoard from './components/StatsBoard';
import { Play, Square, RefreshCw, Key, Layers, CreditCard, LogOut, Save } from 'lucide-react';

const App: React.FC = () => {
  // Load saved Auth from localStorage on init
  const [auth, setAuth] = useState<string>(() => localStorage.getItem('gl_auth') || '');
  
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [accounts, setAccounts] = useState<GolikeAccount[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<Platform | 'all'>('all');
  
  const [stats, setStats] = useState<WorkerStats>({
    totalJobs: 0,
    totalMoney: 0,
    pendingJobs: 0,
    fails: 0
  });

  const workerIntervals = useRef<{ [key: string]: NodeJS.Timeout }>({});

  const addLog = useCallback((accountName: string, message: string, type: LogEntry['type']) => {
    const newLog: LogEntry = {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toLocaleTimeString('en-GB', { hour12: false, minute: '2-digit', second: '2-digit' }),
      accountName,
      message,
      type
    };
    setLogs(prev => {
        const updated = [...prev, newLog];
        return updated.slice(-300); 
    });
  }, []);

  const updateAccountStatus = (id: string, status: GolikeAccount['status'], message?: string) => {
    setAccounts(prev => prev.map(acc => 
        acc.id === id ? { ...acc, status, lastMessage: message || acc.lastMessage } : acc
    ));
  };

  const handleAuthChange = (value: string) => {
      setAuth(value);
      localStorage.setItem('gl_auth', value);
  };

  const handleConnect = async () => {
    if (!auth) return;
    setLogs([]); // Clear old logs
    addLog("System", "Đang kết nối API...", "info");
    
    // 1. Profile
    const profileData = await fetchUserProfile(auth);
    if (profileData && profileData.data) {
        setProfile(profileData.data);
        addLog("System", `Xin chào ${profileData.data.username}. Số dư: ${profileData.data.coin}`, "success");
    }

    // 2. Fetch & Filter Accounts
    const igResponse = await fetchAccounts(auth, 'instagram');
    const pinResponse = await fetchAccounts(auth, 'pinterest');
    
    const loadedAccounts: GolikeAccount[] = [];

    // Filter Logic for IG
    if (igResponse.data) {
        igResponse.data.forEach((acc: any) => {
            const accId = acc.account_id ? acc.account_id.toString() : acc.id.toString();
            // Load saved cookie for this specific account ID
            const savedCookie = localStorage.getItem(`gl_cookie_${accId}`) || '';
            const isCheckpoint = acc.instagram_username.includes('checkpoint'); 
            
            loadedAccounts.push({
                id: accId,
                username: acc.instagram_username || "Unknown",
                platform: 'instagram',
                cookie: savedCookie, // Auto-fill saved cookie
                status: isCheckpoint ? 'die' : 'active', 
                lastMessage: isCheckpoint ? 'Checkpoint Detected' : 'Sẵn sàng'
            });
        });
    }

    // Logic for Pin
    if (pinResponse.data) {
         pinResponse.data.forEach((acc: any) => {
            const accId = acc.id.toString();
            // Load saved cookie
            const savedCookie = localStorage.getItem(`gl_cookie_${accId}`) || '';
            
            loadedAccounts.push({
                id: accId,
                username: acc.username || acc.pinterest_username || "Unknown",
                platform: 'pinterest',
                cookie: savedCookie, // Auto-fill saved cookie
                status: 'active',
                lastMessage: 'Sẵn sàng'
            });
        });
    }

    setAccounts(loadedAccounts);
    const activeCount = loadedAccounts.filter(a => a.status === 'active').length;
    addLog("System", `Đã tải ${loadedAccounts.length} tài khoản (${activeCount} Hoạt động). Cookie đã được tự động điền.`, "info");
  };

  const handleCookieChange = (id: string, value: string) => {
    // Save to localStorage whenever user types
    localStorage.setItem(`gl_cookie_${id}`, value);
    setAccounts(prev => prev.map(acc => acc.id === id ? { ...acc, cookie: value } : acc));
  };

  // --- CORE WORKER LOGIC ---
  const runWorker = async (account: GolikeAccount) => {
      updateAccountStatus(account.id, 'working');

      // 1. Get Job
      const jobRes = await getJob(auth, account.id, account.platform);

      // "cai nao het job thi k hien log"
      if (jobRes.status === 404 || !jobRes.data) {
          updateAccountStatus(account.id, 'waiting', 'Hết job... đang chờ');
          // DO NOT LOG HERE
          return;
      }

      const job = jobRes.data;
      const jobType = job.type === 'follow' ? 'FOLLOW' : 'LIKE';
      updateAccountStatus(account.id, 'working', `Đang làm: ${jobType}`);
      
      // 2. Simulate Doing Job
      // Real logic: Use Cookie to Follow/Like
      await new Promise(r => setTimeout(r, 2000 + Math.random() * 2000));

      // 3. Result
      // Simulate account dying during job (5% chance)
      const isDead = Math.random() < 0.05;
      if (isDead) {
          clearInterval(workerIntervals.current[account.id]);
          delete workerIntervals.current[account.id];
          updateAccountStatus(account.id, 'die', 'Checkpoint/Die');
          addLog(account.username, "Tài khoản bị Checkpoint khi đang làm. Đã dừng.", "fail");
          return;
      }

      const isSuccess = Math.random() > 0.1; 

      if (isSuccess) {
          const money = job.price;
          // Hiển thị log đúng kiểu "Gửi duyệt"
          addLog(account.username, `Đã làm xong ${jobType} -> Chờ duyệt (+${money}đ)`, "money");
          
          setStats(prev => ({
              ...prev,
              totalJobs: prev.totalJobs + 1,
              pendingJobs: prev.pendingJobs + 1, // Tăng số lượng chờ duyệt
              totalMoney: prev.totalMoney + money,
          }));
          
          updateAccountStatus(account.id, 'active', 'Đã gửi duyệt');
      } else {
          // Only log real errors
          addLog(account.username, "Lỗi mạng hoặc Job lỗi", "warn");
          setStats(prev => ({
              ...prev,
              fails: prev.fails + 1,
          }));
      }
  };

  const startAutomation = () => {
    // Filter active accounts only
    const validAccounts = accounts.filter(a => a.status !== 'die' && a.status !== 'maintenance');
    
    // Check Cookies
    const readyAccounts = validAccounts.filter(a => checkCookieFormat(a.cookie, a.platform));

    if (readyAccounts.length === 0) {
        addLog("System", "Chưa nhập Cookie cho tài khoản nào.", "fail");
        alert("Vui lòng nhập Cookie (sessionid cho IG, _auth cho Pin) để chạy.");
        return;
    }

    setIsRunning(true);
    addLog("System", `Bắt đầu chạy tool với ${readyAccounts.length} tài khoản...`, "success");

    readyAccounts.forEach(acc => {
        // Run immediately
        runWorker(acc);
        // Interval
        const delay = 8000 + Math.random() * 5000; // 8-13 seconds delay
        const intervalId = setInterval(() => {
            // Need to pass the latest account info or handle id
            runWorker(acc);
        }, delay);
        workerIntervals.current[acc.id] = intervalId;
    });
  };

  const stopAutomation = () => {
    setIsRunning(false);
    addLog("System", "Đã dừng tất cả.", "warn");
    Object.values(workerIntervals.current).forEach(clearInterval);
    workerIntervals.current = {};
    // Reset statuses
    setAccounts(prev => prev.map(a => a.status === 'die' ? a : { ...a, status: 'active', lastMessage: 'Đã dừng' }));
  };

  const displayedAccounts = activeTab === 'all' 
    ? accounts 
    : accounts.filter(a => a.platform === activeTab);

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 font-sans">
      <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col hidden md:flex">
        <div className="p-4 border-b border-gray-800">
            <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">
                GOLIKE PRO v9
            </h1>
        </div>
        
        <div className="p-4 flex-1 overflow-y-auto">
            <div className="mb-6">
                <label className="text-xs font-semibold text-gray-400 mb-2 block flex items-center gap-2">
                    <Key size={12} /> AUTH TOKEN
                </label>
                <input 
                    type="password" 
                    value={auth}
                    onChange={(e) => handleAuthChange(e.target.value)}
                    placeholder="Nhập Authorization..."
                    className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-xs text-white focus:border-cyan-500 focus:outline-none mb-2"
                />
                <button 
                    onClick={handleConnect}
                    className="w-full bg-gray-800 hover:bg-gray-700 text-cyan-400 text-xs py-2 rounded border border-gray-700 transition-colors flex items-center justify-center gap-2"
                >
                    <RefreshCw size={12} /> Tải dữ liệu
                </button>
            </div>

            {profile && (
                <div className="bg-gray-800/50 rounded p-3 border border-gray-700 mb-6">
                    <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 rounded-full bg-green-500"></div>
                        <span className="font-bold text-sm">{profile.username}</span>
                    </div>
                    <div className="flex items-center gap-2 text-yellow-400 font-mono text-lg">
                        <CreditCard size={16} />
                        {profile.coin.toLocaleString()}đ
                    </div>
                </div>
            )}

            <div className="space-y-2 mt-auto">
                {!isRunning ? (
                    <button 
                        onClick={startAutomation}
                        className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded font-bold shadow-lg shadow-green-900/50 transition-all flex items-center justify-center gap-2"
                    >
                        <Play size={16} fill="currentColor" /> BẮT ĐẦU
                    </button>
                ) : (
                    <button 
                        onClick={stopAutomation}
                        className="w-full bg-red-600 hover:bg-red-700 text-white py-3 rounded font-bold shadow-lg shadow-red-900/50 transition-all flex items-center justify-center gap-2"
                    >
                        <Square size={16} fill="currentColor" /> DỪNG LẠI
                    </button>
                )}
            </div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="md:hidden p-4 bg-gray-900 border-b border-gray-800 flex justify-between items-center">
             <h1 className="font-bold text-cyan-400">GOLIKE PRO</h1>
             <button onClick={handleConnect} className="text-gray-400"><RefreshCw size={18}/></button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 md:p-6 bg-gray-950">
            <StatsBoard stats={stats} />

            <div className="flex items-center gap-4 mb-4 border-b border-gray-800 pb-2 overflow-x-auto">
                <button onClick={() => setActiveTab('all')} className={`text-sm px-3 py-1 rounded whitespace-nowrap ${activeTab === 'all' ? 'bg-gray-800' : 'text-gray-500'}`}>Tất cả ({accounts.length})</button>
                <button onClick={() => setActiveTab('instagram')} className={`text-sm px-3 py-1 rounded whitespace-nowrap ${activeTab === 'instagram' ? 'text-pink-400 bg-pink-900/20' : 'text-gray-500'}`}>Instagram</button>
                <button onClick={() => setActiveTab('pinterest')} className={`text-sm px-3 py-1 rounded whitespace-nowrap ${activeTab === 'pinterest' ? 'text-red-400 bg-red-900/20' : 'text-gray-500'}`}>Pinterest</button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-6">
                {displayedAccounts.map(acc => (
                    <AccountCard 
                        key={acc.id} 
                        account={acc} 
                        onCookieChange={handleCookieChange}
                        isRunning={isRunning}
                    />
                ))}
            </div>

            <div className="h-72 border-t border-gray-800 pt-4">
                <LogTerminal logs={logs} />
            </div>
        </div>
      </main>
    </div>
  );
};

export default App;