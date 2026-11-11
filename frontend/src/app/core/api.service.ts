import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  ApiStatus,
  CnpjCard,
  ContactPayload,
  ContactResponse,
  OrderPayload,
  OrderResponse,
  StudioIssuePayload,
  StudioIssueResponse,
  StudioStatusResponse,
  StudioUnlockResponse,
  AccountAck,
  CompanyLoginResponse,
  CompanyOverview,
  CompanyRoundRow,
  FormQuote,
  InvitationRoster,
  ListQuote,
  InvitationRetryResult,
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

  lookupCnpj(cnpj: string): Observable<CnpjCard> {
    const digits = cnpj.replace(/\D/g, '');
    return this.http.get<CnpjCard>(`${this.base}/cnpj/${digits}`);
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

  confirmAccount(token: string): Observable<AccountAck> {
    return this.http.post<AccountAck>(`${this.base}/company/confirm`, { token });
  }

  resendConfirmation(email: string): Observable<AccountAck> {
    return this.http.post<AccountAck>(`${this.base}/company/confirm/resend`, { email });
  }

  forgotPassword(email: string): Observable<AccountAck> {
    return this.http.post<AccountAck>(`${this.base}/company/password/forgot`, { email });
  }

  resetPassword(token: string, password: string): Observable<AccountAck> {
    return this.http.post<AccountAck>(`${this.base}/company/password/reset`, { token, password });
  }

  getCompanyOverview(passage: string, round: string): Observable<CompanyOverview> {
    return this.http.get<CompanyOverview>(`${this.base}/company/overview`, {
      headers: new HttpHeaders({ 'X-Company-Token': passage }),
      params: { round },
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

  quoteCompanyInvitations(passage: string, file: File): Observable<ListQuote> {
    const body = new FormData();
    body.append('file', file, file.name);
    return this.http.post<ListQuote>(`${this.base}/company/invitations/quote`, body, {
      headers: new HttpHeaders({ 'X-Company-Token': passage }),
    });
  }

  uploadCompanyInvitations(
    passage: string,
    file: File,
    method = '',
    skip = false,
  ): Observable<InvitationUploadResult> {
    const body = new FormData();
    body.append('file', file, file.name);
    body.append('method', method);
    body.append('skip', skip ? '1' : '');
    return this.http.post<InvitationUploadResult>(`${this.base}/company/invitations`, body, {
      headers: new HttpHeaders({ 'X-Company-Token': passage }),
    });
  }

  chooseFormCharge(passage: string, chargeId: string, method: string): Observable<FormQuote> {
    return this.http.post<FormQuote>(
      `${this.base}/company/charges/${chargeId}`,
      { method },
      { headers: new HttpHeaders({ 'X-Company-Token': passage }) },
    );
  }

  retryCompanyInvitations(passage: string): Observable<InvitationRetryResult> {
    return this.http.post<InvitationRetryResult>(`${this.base}/company/invitations/retry`, null, {
      headers: new HttpHeaders({ 'X-Company-Token': passage }),
    });
  }

  private studioHeaders(token: string): HttpHeaders {
    return new HttpHeaders({ 'X-Studio-Token': token });
  }
}
