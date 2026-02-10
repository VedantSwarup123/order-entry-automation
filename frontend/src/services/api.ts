import axios from 'axios';

const api = axios.create({ baseURL: '/api/v1' });

// ---- Types ----

export interface DashboardStats {
  total_orders: number;
  orders_today: number;
  success_rate: number;
  total_revenue: number;
  pending_reviews: number;
  trends: {
    orders_change: number;
    revenue_change: number;
  };
}

export interface OrderSummary {
  id: string;
  customer_id: string;
  customer_name: string;
  po_number: string;
  source: string;
  total_amount: number;
  total_quantity: number;
  status: string;
  created_at: string;
  errors: string;
  item_count: number;
}

export interface OrderDetail extends OrderSummary {
  order_date: string;
  source_ref: string;
  ship_to_name: string;
  ship_to_line1: string;
  ship_to_city: string;
  ship_to_state: string;
  ship_to_postal_code: string;
  ship_to_country: string;
  notes: string;
  destinations: string[];
  line_items: LineItem[];
  review: {
    id: number;
    confidence: number;
    extraction_method: string;
    anomalies: string[];
    status: string;
  } | null;
  sap_order_type: string | null;
  sap_data: Record<string, unknown> | null;
}

export interface LineItem {
  id: number;
  sku: string;
  description: string;
  quantity: number;
  unit_price: number;
  uom: string;
  line_total: number;
}

export interface PaginatedOrders {
  orders: OrderSummary[];
  total: number;
  page: number;
  pages: number;
}

export interface OrdersByDay {
  date: string;
  count: number;
  revenue: number;
}

export interface OrdersBySource {
  source: string;
  count: number;
}

export interface OrdersByStatus {
  status: string;
  count: number;
}

export interface CustomerSummary {
  customer_id: string;
  customer_name: string;
  order_count: number;
  total_revenue: number;
  last_order: string;
}

export interface CustomerDetail extends CustomerSummary {
  orders: OrderSummary[];
  avg_order_value: number;
}

export interface TopCustomer {
  customer_id: string;
  customer_name: string;
  order_count: number;
  total_revenue: number;
}

export interface AuditEntry {
  id: number;
  order_id: string;
  action: string;
  detail: string;
  timestamp: string;
}

export interface InboxActivity {
  type: string;
  description: string;
  timestamp: string;
  status: string;
}

export interface IntegrationStatus {
  gmail: string;
  outlook: string;
  sheets: string;
  slack: string;
}

export interface RoutingRule {
  name: string;
  condition: string;
  destination: string;
}

export interface ReviewItem {
  id: number;
  order_id: string;
  source: string;
  customer_name: string;
  po_number: string;
  confidence: number;
  extraction_method: string;
  anomalies: string[];
  original_text: string;
  extracted_data: Record<string, unknown>;
  status: string;
  reviewer_notes: string;
  reviewed_at: string | null;
  created_at: string;
}

export interface ReviewDetail extends ReviewItem {
  order: OrderSummary | null;
  line_items: LineItem[];
}

export interface ReviewCount {
  pending: number;
  total: number;
}

// ---- API Calls ----

export const getStats = () => api.get<DashboardStats>('/stats');

export const getOrders = (params?: {
  limit?: number;
  offset?: number;
  status?: string;
  source?: string;
  search?: string;
  sort?: string;
  order?: 'asc' | 'desc';
}) => api.get<PaginatedOrders>('/orders', { params });

export const getOrder = (id: string) => api.get<OrderDetail>(`/orders/${id}`);

export const createOrder = (data: Record<string, unknown>) =>
  api.post('/orders', data, { headers: { 'X-API-Key': 'dev-api-key-change-me' } });

export const getCustomers = () => api.get<{ customers: CustomerSummary[] }>('/customers');

export const getCustomer = (id: string) => api.get<CustomerDetail>(`/customers/${id}`);

export const getOrdersByDay = (days?: number) =>
  api.get<OrdersByDay[]>('/analytics/orders-by-day', { params: { days } });

export const getOrdersBySource = () => api.get<OrdersBySource[]>('/analytics/orders-by-source');

export const getOrdersByStatus = () => api.get<OrdersByStatus[]>('/analytics/orders-by-status');

export const getTopCustomers = (limit?: number) =>
  api.get<TopCustomer[]>('/analytics/top-customers', { params: { limit } });

export const getRecentActivity = () => api.get<AuditEntry[]>('/inbox/recent');

export const uploadCsv = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/inbox/upload-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const getIntegrations = () => api.get<IntegrationStatus>('/settings/integrations');

export const getRoutingRules = () => api.get<{ rules: RoutingRule[] }>('/settings/routing-rules');

// Review Queue
export const getReviewItems = (params?: { status?: string; limit?: number; offset?: number }) =>
  api.get<{ items: ReviewItem[]; total: number; pending_count: number }>('/review', { params });

export const getReviewCount = () => api.get<ReviewCount>('/review/count');

export const getReviewItem = (id: number) => api.get<ReviewDetail>(`/review/${id}`);

export const actionReviewItem = (id: number, data: { action: string; notes?: string; modified_data?: Record<string, unknown> }) =>
  api.post(`/review/${id}`, data);

export default api;
