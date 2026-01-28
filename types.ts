export type Platform = 'instagram' | 'pinterest' | 'twitter';

export interface GolikeAccount {
  id: string;
  username: string;
  platform: Platform;
  cookie: string;
  status: 'active' | 'die' | 'maintenance' | 'waiting' | 'working';
  lastMessage?: string; // To display status on card without spamming logs
}

export interface UserProfile {
  username: string;
  coin: number;
}

export type LogType = 'info' | 'success' | 'fail' | 'warn' | 'money' | 'skip';

export interface LogEntry {
  id: string;
  timestamp: string;
  accountName: string;
  message: string;
  type: LogType;
}

export interface WorkerStats {
  totalJobs: number;
  totalMoney: number;
  pendingJobs: number; // Changed from successRate to pendingJobs (Chờ duyệt)
  fails: number;
}

export interface Job {
  id: string;
  link: string;
  type: string;
  object_id: string;
  price: number;
}