import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  ApiStatus,
  ContactPayload,
  ContactResponse,
  StudioIssuePayload,
  StudioIssueResponse,
  StudioStatusResponse,
  StudioUnlockResponse,
  BlockwallStatus,
  BlockwallUnlockResponse,
  CompanyLoginResponse,
  CompanyOverview,
} from './models';

/**
 * HTTP client for the Stephan FastAPI backend.
 * All versioned endpoints live under /api/v1.
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  submitContact(payload: ContactPayload): Observable<ContactResponse> {
    return this.http.post<ContactResponse>(`${this.base}/contact`, payload);
  }

  getStatus(): Observable<ApiStatus> {
    return this.http.get<ApiStatus>(`${this.base}/status`);
  }

  getStudioStatus(): Observable<StudioStatusResponse> {
    return this.http.get<StudioStatusResponse>(`${this.base}/studio/status`);
  }

  unlockStudio(token: string): Observable<StudioUnlockResponse> {
    return this.http.post<StudioUnlockResponse>(`${this.base}/studio/unlock`, {}, {
      headers: this.studioHeaders(token),
    });
  }

  submitStudioIssue(token: string, payload: StudioIssuePayload): Observable<StudioIssueResponse> {
    return this.http.post<StudioIssueResponse>(`${this.base}/studio/issues`, payload, {
      headers: this.studioHeaders(token),
    });
  }

  getBlockwall(): Observable<BlockwallStatus> {
    return this.http.get<BlockwallStatus>(`${this.base}/blockwall/status`);
  }

  unlockBlockwall(password: string): Observable<BlockwallUnlockResponse> {
    return this.http.post<BlockwallUnlockResponse>(`${this.base}/blockwall/unlock`, { password });
  }

  resumeBlockwall(passage: string): Observable<{ success: boolean }> {
    return this.http.post<{ success: boolean }>(`${this.base}/blockwall/resume`, { passage });
  }

  loginCompany(username: string, password: string): Observable<CompanyLoginResponse> {
    return this.http.post<CompanyLoginResponse>(`${this.base}/company/login`, { username, password });
  }

  getCompanyOverview(passage: string): Observable<CompanyOverview> {
    return this.http.get<CompanyOverview>(`${this.base}/company/overview`, {
      headers: new HttpHeaders({ 'X-Company-Token': passage }),
    });
  }

  private studioHeaders(token: string): HttpHeaders {
    return new HttpHeaders({ 'X-Studio-Token': token });
  }
}
