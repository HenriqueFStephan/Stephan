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

  private studioHeaders(token: string): HttpHeaders {
    return new HttpHeaders({ 'X-Studio-Token': token });
  }
}
