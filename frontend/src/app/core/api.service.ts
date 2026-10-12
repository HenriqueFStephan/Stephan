import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  ApiStatus,
  ContactPayload,
  ContactResponse,
  OrderPayload,
  OrderResponse,
  StudioIssuePayload,
  StudioIssueResponse,
  StudioStatusResponse,
  StudioUnlockResponse,
  CompanyLoginResponse,
  CompanyOverview,
  CompanyRoundRow,
  InvitationRoster,
  InvitationUploadResult,
  ToolAccessResult,
  ToolDraft,
  ToolSubmitResult,
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

  submitOrder(payload: OrderPayload): Observable<OrderResponse> {
    return this.http.post<OrderResponse>(`${this.base}/orders`, payload);
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

  loginCompany(username: string, password: string): Observable<CompanyLoginResponse> {
    return this.http.post<CompanyLoginResponse>(`${this.base}/company/login`, { username, password });
  }

  getCompanyOverview(passage: string): Observable<CompanyOverview> {
    return this.http.get<CompanyOverview>(`${this.base}/company/overview`, {
      headers: new HttpHeaders({ 'X-Company-Token': passage }),
    });
  }

  getCompanyInvitations(passage: string): Observable<InvitationRoster> {
    return this.http.get<InvitationRoster>(`${this.base}/company/invitations`, {
      headers: new HttpHeaders({ 'X-Company-Token': passage }),
    });
  }

  getCompanyRounds(passage: string): Observable<CompanyRoundRow[]> {
    return this.http.get<CompanyRoundRow[]>(`${this.base}/company/rounds`, {
      headers: new HttpHeaders({ 'X-Company-Token': passage }),
    });
  }

  openTool(token: string): Observable<ToolAccessResult> {
    return this.http.post<ToolAccessResult>(`${this.base}/tool/access`, { token });
  }

  saveToolDraft(token: string, draft: ToolDraft): Observable<ToolSubmitResult> {
    return this.http.post<ToolSubmitResult>(`${this.base}/tool/drafts`, { token, ...draft });
  }

  submitTool(
    token: string,
    answers: number[],
    demographics: Record<string, string>,
  ): Observable<ToolSubmitResult> {
    return this.http.post<ToolSubmitResult>(`${this.base}/tool/responses`, {
      token,
      answers,
      demographics,
    });
  }

  uploadCompanyInvitations(passage: string, file: File): Observable<InvitationUploadResult> {
    const body = new FormData();
    body.append('file', file, file.name);
    return this.http.post<InvitationUploadResult>(`${this.base}/company/invitations`, body, {
      headers: new HttpHeaders({ 'X-Company-Token': passage }),
    });
  }

  private studioHeaders(token: string): HttpHeaders {
    return new HttpHeaders({ 'X-Studio-Token': token });
  }
}
