import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../theme/colors';
import { ApiService } from '../services/api';

export default function CalendarScreen() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadCalendar = useCallback(async () => {
    try {
      const data = await ApiService.getCalendar();
      setEvents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadCalendar();
  }, [loadCalendar]);

  const renderEvent = ({ item }: { item: any }) => {
    const isHoliday = item.is_holiday || item.event_type?.includes('बिदा');
    const isExam = item.event_type?.includes('परीक्षा');

    return (
      <View style={styles.card}>
        <View
          style={[
            styles.dateBadge,
            isHoliday
              ? { backgroundColor: '#FEE2E2', borderColor: '#FCA5A5' }
              : isExam
              ? { backgroundColor: '#FEF3C7', borderColor: '#FCD34D' }
              : { backgroundColor: '#EFF6FF', borderColor: '#BFDBFE' },
          ]}
        >
          <Text
            style={[
              styles.dateMonth,
              isHoliday
                ? { color: '#B91C1C' }
                : isExam
                ? { color: '#B45309' }
                : { color: Colors.primary },
            ]}
          >
            {(item.start_date || item.event_date)?.slice(5, 7) || '०१'} महिना
          </Text>
          <Text
            style={[
              styles.dateDay,
              isHoliday
                ? { color: '#B91C1C' }
                : isExam
                ? { color: '#B45309' }
                : { color: Colors.primary },
            ]}
          >
            {(item.start_date || item.event_date)?.slice(8, 10) || '०१'}
          </Text>
        </View>

        <View style={styles.eventInfo}>
          <View style={styles.typeRow}>
            <Text
              style={[
                styles.typeTag,
                isHoliday
                  ? { backgroundColor: '#FEE2E2', color: '#B91C1C' }
                  : { backgroundColor: '#F1F5F9', color: Colors.textMuted },
              ]}
            >
              {item.event_type || 'शैक्षिक कार्यक्रम'}
            </Text>
            {isHoliday && <Text style={styles.holidayAlert}>सार्वजनिक बिदा</Text>}
          </View>
          <Text style={styles.eventTitle}>{item.title || item.title_ne}</Text>
          {item.description_ne ? (
            <Text style={styles.eventDesc}>{item.description_ne}</Text>
          ) : null}
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>शैक्षिक क्यालेन्डर</Text>
        <Text style={styles.headerSub}>शैक्षिक सत्र २०८१/८२ का महत्वपूर्ण मिति तथा कार्यक्रमहरू</Text>
      </View>

      {loading ? (
        <View style={styles.centerLoading}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>क्यालेन्डर लोड हुँदैछ...</Text>
        </View>
      ) : (
        <FlatList
          data={events}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderEvent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                loadCalendar();
              }}
              colors={[Colors.primary]}
            />
          }
          contentContainerStyle={{ padding: 12, paddingBottom: 24 }}
          ListEmptyComponent={
            <Text style={styles.emptyText}>क्यालेन्डरमा तत्काल कुनै कार्यक्रम दर्ता छैन।</Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  header: {
    backgroundColor: Colors.primary,
    paddingTop: 45,
    paddingBottom: 15,
    paddingHorizontal: 16,
  },
  headerTitle: { color: '#fff', fontSize: 17, fontWeight: 'bold' },
  headerSub: { color: Colors.gold, fontSize: 11, marginTop: 2 },
  centerLoading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  loadingText: { marginTop: 8, fontSize: 12, color: Colors.textMuted },
  card: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  dateBadge: {
    width: 52,
    height: 52,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dateMonth: { fontSize: 9, fontWeight: 'bold', textTransform: 'uppercase' },
  dateDay: { fontSize: 18, fontWeight: 'bold', marginTop: 1 },
  eventInfo: { flex: 1 },
  typeRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 2 },
  typeTag: { fontSize: 9, fontWeight: 'bold', paddingHorizontal: 6, paddingVertical: 1, borderRadius: 4 },
  holidayAlert: { fontSize: 9, fontWeight: 'bold', color: Colors.danger },
  eventTitle: { fontSize: 13, fontWeight: 'bold', color: Colors.textMain },
  eventDesc: { fontSize: 11, color: Colors.textMuted, marginTop: 2 },
  emptyText: { textAlign: 'center', padding: 30, color: Colors.textMuted, fontSize: 12 },
});
