export interface User { id: string; name: string; email: string; email_verified: boolean; role: string; phone: string | null; date_of_birth: string | null; blood_group: string | null; worker_application_status?: string | null; }
export function accountHome(user: User) {
  if (user.role === "admin") return "/admin";
  if (user.role === "worker") return "/worker";
  return user.worker_application_status ? "/workers/apply" : "/community";
}
export interface Session { id: string; created_at: number; last_seen_at: number; expires_at: number; current: boolean; }
