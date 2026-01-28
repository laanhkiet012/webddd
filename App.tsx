import React, { useState, useCallback, useEffect } from 'react';
import { GolikeAccount, LogEntry, Platform, UserProfile, WorkerStats } from './types';
import { golikeService, checkCookieFormat } from './services/golikeService';
import LogTerminal from './components/LogTerminal';
import AccountCard from './components/AccountCard';
import StatsBoard from './components/StatsBoard';
import { Play, Square, RefreshCw, Key, CreditCard, Wifi, WifiOff, Check, CheckCheck } from 'lucide-react';

const App: React.FC = () => {
    const [auth, setAuth] = useState<string>(() => localStorage.getItem('gl_auth') || '');
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [accounts, setAccounts] = useState<GolikeAccount[]>([]);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isRunning, setIsRunning] = useState<boolean>(false);
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const [activeTab, setActiveTab] = useState<Platform | 'all'>('all');

    // Account selection state
    const [selectedAccounts, setSelectedAccounts] = useState<Set<string>>(new Set());

    const [stats, setStats] = useState<WorkerStats>({
        totalJobs: 0,
        totalMoney: 0,
        pendingJobs: 0,
        fails: 0
    });

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

    // Connect to WebSocket backend
    useEffect(() => {
        const connectWS = async () => {
            try {
                await golikeService.connect();
                setIsConnected(true);
                addLog("System", "Đã kết nối backend server", "success");
            } catch (e) {
                setIsConnected(false);
                addLog("System", "Không thể kết nối server - Hãy chạy: npm run server", "fail");
            }
        };

        connectWS();

        // Setup event handlers
        golikeService.on('profile', (data) => {
            setProfile(data.data);
        });

        golikeService.on('accounts', (data) => {
            const loadedAccounts: GolikeAccount[] = data.data.map((acc: any) => {
                const savedCookie = localStorage.getItem(`gl_cookie_${acc.id}`) || '';
                return {
                    id: acc.id,
                    username: acc.username,
                    platform: acc.platform,
                    cookie: savedCookie,
                    status: acc.status || 'active',
                    lastMessage: 'Sẵn sàng'
                };
            });
            setAccounts(loadedAccounts);
            // Auto-select all accounts on load
            setSelectedAccounts(new Set(loadedAccounts.map(a => a.id)));
        });

        golikeService.on('log', (data) => {
            addLog(data.accountName, data.message, data.logType);
        });

        golikeService.on('accountStatus', (data) => {
            updateAccountStatus(data.accountId, data.status, data.message);
        });

        golikeService.on('stats', (data) => {
            setStats(prev => ({
                ...prev,
                totalJobs: prev.totalJobs + (data.jobsDone || 0),
                totalMoney: prev.totalMoney + (data.money || 0),
                pendingJobs: prev.pendingJobs + (data.pending || 0),
                fails: prev.fails + (data.fails || 0)
            }));
        });

        return () => {
            golikeService.disconnect();
        };
    }, [addLog]);

    const handleAuthChange = (value: string) => {
        setAuth(value);
        localStorage.setItem('gl_auth', value);
    };

    const handleConnect = async () => {
        if (!auth) return;
        if (!isConnected) {
            addLog("System", "Server chưa kết nối - Hãy chạy: npm run server", "fail");
            return;
        }
        setLogs([]);
        addLog("System", "Đang kết nối Golike API...", "info");
        golikeService.connectToGolike(auth);
    };

    const handleCookieChange = (id: string, value: string) => {
        localStorage.setItem(`gl_cookie_${id}`, value);
        setAccounts(prev => prev.map(acc => acc.id === id ? { ...acc, cookie: value } : acc));
    };

    // Toggle account selection
    const toggleAccount = (id: string) => {
        setSelectedAccounts(prev => {
            const newSet = new Set(prev);
            if (newSet.has(id)) {
                newSet.delete(id);
            } else {
                newSet.add(id);
            }
            return newSet;
        });
    };

    // Select/Deselect all in current tab
    const selectAllInTab = () => {
        const tabAccounts = activeTab === 'all' ? accounts : accounts.filter(a => a.platform === activeTab);
        const allSelected = tabAccounts.every(a => selectedAccounts.has(a.id));

        setSelectedAccounts(prev => {
            const newSet = new Set(prev);
            tabAccounts.forEach(a => {
                if (allSelected) {
                    newSet.delete(a.id);
                } else {
                    newSet.add(a.id);
                }
            });
            return newSet;
        });
    };

    // Select only current platform
    const selectOnlyPlatform = (platform: Platform) => {
        const platformAccounts = accounts.filter(a => a.platform === platform);
        setSelectedAccounts(new Set(platformAccounts.map(a => a.id)));
        addLog("System", `Đã chọn ${platformAccounts.length} tài khoản ${platform.toUpperCase()}`, "info");
    };

    const startAutomation = () => {
        if (!isConnected) {
            addLog("System", "Server chưa kết nối!", "fail");
            return;
        }

        // Only run selected accounts
        const selectedList = accounts.filter(a => selectedAccounts.has(a.id));
        const validAccounts = selectedList.filter(a => a.status !== 'die' && a.status !== 'maintenance');
        const readyAccounts = validAccounts.filter(a => checkCookieFormat(a.cookie, a.platform));

        if (readyAccounts.length === 0) {
            addLog("System", "Chưa chọn tài khoản nào có Cookie hợp lệ.", "fail");
            alert("Vui lòng chọn tài khoản và nhập Cookie để chạy.");
            return;
        }

        addLog("System", `Đang chạy ${readyAccounts.length} tài khoản đã chọn...`, "success");
        setIsRunning(true);
        golikeService.startAutomation(readyAccounts, auth);
    };

    const stopAutomation = () => {
        setIsRunning(false);
        golikeService.stopAutomation();
        setAccounts(prev => prev.map(a => a.status === 'die' ? a : { ...a, status: 'active', lastMessage: 'Đã dừng' }));
    };

    const displayedAccounts = activeTab === 'all'
        ? accounts
        : accounts.filter(a => a.platform === activeTab);

    const selectedCountInTab = displayedAccounts.filter(a => selectedAccounts.has(a.id)).length;

    return (
        <div className="flex h-screen bg-gray-950 text-gray-100 font-sans">
            <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col hidden md:flex">
                <div className="p-4 border-b border-gray-800">
                    <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">
                        GOLIKE PRO v10
                    </h1>
                    <div className={`text-xs mt-1 flex items-center gap-1 ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                        {isConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
                        {isConnected ? 'Server Connected' : 'Server Disconnected'}
                    </div>
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
                            disabled={!isConnected}
                            className="w-full bg-gray-800 hover:bg-gray-700 text-cyan-400 text-xs py-2 rounded border border-gray-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
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
                                disabled={!isConnected}
                                className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded font-bold shadow-lg shadow-green-900/50 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
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
                    <div className="flex items-center gap-2">
                        {isConnected ? <Wifi size={16} className="text-green-400" /> : <WifiOff size={16} className="text-red-400" />}
                        <button onClick={handleConnect} className="text-gray-400"><RefreshCw size={18} /></button>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 md:p-6 bg-gray-950">
                    <StatsBoard stats={stats} />

                    {/* Platform tabs with selection controls */}
                    <div className="flex flex-wrap items-center gap-2 mb-4 border-b border-gray-800 pb-3">
                        <div className="flex items-center gap-2 flex-wrap">
                            <button
                                onClick={() => setActiveTab('all')}
                                className={`text-sm px-3 py-1.5 rounded-lg whitespace-nowrap transition-all ${activeTab === 'all' ? 'bg-gray-700 text-white' : 'text-gray-500 hover:bg-gray-800'}`}
                            >
                                Tất cả ({accounts.length})
                            </button>
                            <button
                                onClick={() => setActiveTab('instagram')}
                                onDoubleClick={() => selectOnlyPlatform('instagram')}
                                className={`text-sm px-3 py-1.5 rounded-lg whitespace-nowrap transition-all ${activeTab === 'instagram' ? 'text-pink-400 bg-pink-900/30 ring-1 ring-pink-500' : 'text-gray-500 hover:bg-gray-800'}`}
                            >
                                📸 IG ({accounts.filter(a => a.platform === 'instagram').length})
                            </button>
                            <button
                                onClick={() => setActiveTab('pinterest')}
                                onDoubleClick={() => selectOnlyPlatform('pinterest')}
                                className={`text-sm px-3 py-1.5 rounded-lg whitespace-nowrap transition-all ${activeTab === 'pinterest' ? 'text-red-400 bg-red-900/30 ring-1 ring-red-500' : 'text-gray-500 hover:bg-gray-800'}`}
                            >
                                📌 Pin ({accounts.filter(a => a.platform === 'pinterest').length})
                            </button>
                            <button
                                onClick={() => setActiveTab('twitter')}
                                onDoubleClick={() => selectOnlyPlatform('twitter')}
                                className={`text-sm px-3 py-1.5 rounded-lg whitespace-nowrap transition-all ${activeTab === 'twitter' ? 'text-blue-400 bg-blue-900/30 ring-1 ring-blue-500' : 'text-gray-500 hover:bg-gray-800'}`}
                            >
                                🐦 X ({accounts.filter(a => a.platform === 'twitter').length})
                            </button>
                        </div>

                        {/* Selection controls */}
                        <div className="flex items-center gap-2 ml-auto">
                            <span className="text-xs text-gray-500">
                                Đã chọn: <span className="text-cyan-400 font-bold">{selectedAccounts.size}/{accounts.length}</span>
                            </span>
                            <button
                                onClick={selectAllInTab}
                                className="text-xs px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 flex items-center gap-1"
                            >
                                <CheckCheck size={12} />
                                {displayedAccounts.every(a => selectedAccounts.has(a.id)) ? 'Bỏ chọn' : 'Chọn tất cả'}
                            </button>
                        </div>
                    </div>

                    {/* Account grid with checkboxes */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 mb-6">
                        {displayedAccounts.map(acc => (
                            <div
                                key={acc.id}
                                className={`relative cursor-pointer transition-all ${selectedAccounts.has(acc.id) ? 'ring-2 ring-cyan-500 rounded-lg' : 'opacity-60'}`}
                                onClick={() => !isRunning && toggleAccount(acc.id)}
                            >
                                {/* Checkbox indicator */}
                                <div className={`absolute top-2 left-2 z-10 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold transition-all ${selectedAccounts.has(acc.id) ? 'bg-cyan-500 text-white' : 'bg-gray-700 text-gray-400'}`}>
                                    {selectedAccounts.has(acc.id) ? <Check size={12} /> : ''}
                                </div>
                                <AccountCard
                                    account={acc}
                                    onCookieChange={handleCookieChange}
                                    isRunning={isRunning}
                                />
                            </div>
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