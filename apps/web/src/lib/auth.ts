export interface User { id: string; name: string; email: string; email_verified: boolean; role: string; }
export interface Session { id: string; created_at: number; last_seen_at: number; expires_at: number; current: boolean; }
