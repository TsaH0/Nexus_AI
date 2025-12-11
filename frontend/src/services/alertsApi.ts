// API Service for Alerts & Notifications

const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface AlertNotifyRequest {
  recipient: string;
  channel: 'whatsapp' | 'email';
  alert_ids?: string[];
  custom_message?: string;
  include_eta?: boolean;
  
  // UTR (Understock Ratio) thresholds
  utr_email_threshold?: number;      // Default: 0.20 - Email if UTR > this value
  utr_whatsapp_threshold?: number;   // Default: 0.50 - WhatsApp if UTR > this value
  
  // OTR (Overstock Ratio) thresholds
  otr_email_threshold?: number;      // Default: 0.50 - Email if OTR > this value
  otr_whatsapp_threshold?: number;   // Default: 1.0 - WhatsApp if OTR > this value
  
  // PDF options
  generate_pdf?: boolean;            // Default: true - Generate PDF report
  attach_pdf_to_email?: boolean;     // Default: true - Attach PDF to email
  send_pdf_via_whatsapp?: boolean;   // Default: true - Send PDF via WhatsApp
}

export interface AlertNotifyResponse {
  success: boolean;
  channel: string;
  recipient: string;
  alerts_sent: number;
  message_id?: string;
  error?: string;
  pdf_generated?: boolean;
  pdf_attached?: boolean;
  thresholds_applied?: {
    utr_threshold: number;
    otr_threshold: number;
  };
}

class AlertsAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, options);
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`API Error: ${response.status} - ${errorText}`);
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  }

  // Send notification (Manual Trigger)
  async sendNotification(data: AlertNotifyRequest): Promise<AlertNotifyResponse> {
    return this.fetch<AlertNotifyResponse>('/alerts/notify', {
      method: 'POST',
      body: JSON.stringify(data),
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Bulk Notification
  async sendBulkNotification(recipients: string[], channel: 'whatsapp' | 'email'): Promise<any> {
    return this.fetch('/alerts/notify/bulk', {
      method: 'POST',
      body: JSON.stringify({ recipients, channel }),
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Acknowledge Alert
  async acknowledgeAlert(alertId: string, by: string, action?: string): Promise<any> {
    return this.fetch('/alerts/acknowledge', {
      method: 'POST',
      body: JSON.stringify({ 
        alert_id: alertId, 
        acknowledged_by: by, 
        action_taken: action 
      }),
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

export const alertsApi = new AlertsAPI();
export default alertsApi;

