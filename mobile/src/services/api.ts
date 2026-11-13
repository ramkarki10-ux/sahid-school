import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// Default to live production Vercel backend
export const API_BASE_URL = 'https://sahid-school.vercel.app';
export const DEFAULT_AVATAR = 'https://sahid-school.vercel.app/static/images/default_avatar.png';

/**
 * Universal Image Path Resolver for Mobile App:
 * Automatically resolves relative URLs (/static/...), Base64 data URLs, and external URLs.
 */
export function resolveImageUrl(photo?: string | null): string {
  if (!photo || !photo.trim()) {
    return DEFAULT_AVATAR;
  }
  const clean = photo.trim();
  if (clean.startsWith('data:image/') || clean.startsWith('http://') || clean.startsWith('https://')) {
    return clean;
  }
  const path = clean.startsWith('/') ? clean : `/${clean}`;
  return `${API_BASE_URL}${path}`;
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach Authorization Bearer token to requests
api.interceptors.request.use(async (config) => {
  try {
    const token = await SecureStore.getItemAsync('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch (e) {
    // secure store unavailable (e.g. web fallback)
  }
  return config;
});

export const ApiService = {
  // 1. Authentication
  login: async (username: string, password: string) => {
    const res = await api.post('/api/mobile/login', { username, password });
    if (res.data.token) {
      await SecureStore.setItemAsync('auth_token', res.data.token);
    }
    return res.data;
  },

  logout: async () => {
    try {
      await SecureStore.deleteItemAsync('auth_token');
    } catch (e) {}
  },

  getProfile: async () => {
    const res = await api.get('/api/mobile/profile');
    return res.data.user;
  },

  // 2. Facebook-Style Dynamic News Feed
  getFeed: async (limit = 20, offset = 0) => {
    const res = await api.get('/api/feed/posts', { params: { limit, offset } });
    return res.data.posts || [];
  },

  createPost: async (content: string, imageUrl?: string, postType = 'post') => {
    const res = await api.post('/api/feed/posts', {
      content,
      image_url: imageUrl,
      post_type: postType,
    });
    return res.data;
  },

  toggleLike: async (postId: number) => {
    const res = await api.post(`/api/feed/posts/${postId}/like`);
    return res.data;
  },

  addComment: async (postId: number, content: string) => {
    const res = await api.post(`/api/feed/posts/${postId}/comment`, { content });
    return res.data;
  },

  deletePost: async (postId: number) => {
    const res = await api.delete(`/api/feed/posts/${postId}`);
    return res.data;
  },

  shareNoticeToFeed: async (noticeId: number) => {
    const res = await api.post(`/api/feed/share-notice/${noticeId}`);
    return res.data;
  },

  // 3. Smart Attendance Tracker
  getAttendanceSummary: async (dateStr?: string) => {
    const res = await api.get('/api/mobile/attendance/summary', {
      params: { date_str: dateStr },
    });
    return res.data;
  },

  getClassAttendance: async (classId: number, dateStr?: string) => {
    const res = await api.get(`/api/mobile/attendance/class/${classId}`, {
      params: { date_str: dateStr },
    });
    return res.data;
  },

  markAttendance: async (classId: number, attendanceDate: string, records: any[]) => {
    const res = await api.post('/api/mobile/attendance/mark', {
      class_id: classId,
      attendance_date: attendanceDate,
      records,
    });
    return res.data;
  },

  // 4. Notices & Information
  getNotices: async (limit = 30) => {
    const res = await api.get('/api/mobile/notices', { params: { limit } });
    return res.data.notices || [];
  },

  // 5. Academic Calendar
  getCalendar: async () => {
    const res = await api.get('/api/mobile/calendar');
    return res.data.events || [];
  },

  // 6. Photo Gallery
  getGallery: async () => {
    const res = await api.get('/api/mobile/gallery');
    return res.data;
  },

  // 7. Classes List
  getClasses: async () => {
    const res = await api.get('/api/mobile/classes');
    return res.data.classes || [];
  },

  // 8. School Administration (विद्यालय प्रशासन: SMC, Guthiyar, Teachers & Leadership)
  getAdministration: async (forceRefresh = false) => {
    const params = forceRefresh ? { _t: Date.now() } : {};
    const res = await api.get('/api/mobile/administration', { params });
    return res.data;
  },

  getSMC: async (forceRefresh = false) => {
    const params = forceRefresh ? { _t: Date.now() } : {};
    const res = await api.get('/api/mobile/administration/smc', { params });
    return res.data.members || [];
  },

  getGuthiyar: async (forceRefresh = false) => {
    const params = forceRefresh ? { _t: Date.now() } : {};
    const res = await api.get('/api/mobile/administration/guthiyar', { params });
    return res.data.members || [];
  },

  getTeachers: async (forceRefresh = false) => {
    const params = forceRefresh ? { _t: Date.now() } : {};
    const res = await api.get('/api/mobile/administration/teachers', { params });
    return res.data.teachers || [];
  },

  getLeadership: async (forceRefresh = false) => {
    const params = forceRefresh ? { _t: Date.now() } : {};
    const res = await api.get('/api/mobile/administration/leadership', { params });
    return res.data.leadership || [];
  },
};

export default api;

