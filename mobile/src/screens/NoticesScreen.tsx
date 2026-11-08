import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
  Linking,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../theme/colors';
import { ApiService, API_BASE_URL } from '../services/api';

export default function NoticesScreen() {
  const [notices, setNotices] = useState<any[]>([]);
  const [filteredNotices, setFilteredNotices] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const categories = ['all', 'सामान्य', 'परीक्षा', 'भर्ना', 'कार्यक्रम', 'बिदा'];

  const loadNotices = useCallback(async () => {
    try {
      const data = await ApiService.getNotices();
      setNotices(data);
      applyFilter(data, selectedCategory);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    loadNotices();
  }, [loadNotices]);

  const applyFilter = (data: any[], cat: string) => {
    if (cat === 'all') {
      setFilteredNotices(data);
    } else {
      setFilteredNotices(data.filter((n) => n.category === cat));
    }
  };

  const handleCategorySelect = (cat: string) => {
    setSelectedCategory(cat);
    applyFilter(notices, cat);
  };

  const handleShareToFeed = async (noticeId: number) => {
    Alert.alert(
      'फिडमा सेयर',
      'के तपाईं यो आधिकारिक सूचनालाई न्युज फिडमा सेयर गर्न चाहनुहुन्छ?',
      [
        { text: 'रद्द', style: 'cancel' },
        {
          text: 'सेयर गर्नुहोस्',
          onPress: async () => {
            try {
              const res = await ApiService.shareNoticeToFeed(noticeId);
              Alert.alert('सफल', res.message || 'सूचना फिडमा सेयर भयो!');
            } catch (e) {
              Alert.alert('त्रुटि', 'सेयर गर्न सकिएन।');
            }
          },
        },
      ]
    );
  };

  const handleDownloadAttachment = (attachmentUrl: string) => {
    const fullUrl = attachmentUrl.startsWith('http')
      ? attachmentUrl
      : `${API_BASE_URL}${attachmentUrl}`;
    Linking.openURL(fullUrl).catch(() => {
      Alert.alert('त्रुटि', 'कागजात खोल्न सकिएन।');
    });
  };

  const renderNotice = ({ item }: { item: any }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.catBadge}>
          <Text style={styles.catBadgeText}>{item.category || 'सूचना'}</Text>
        </View>
        <Text style={styles.dateText}>प्रकाशित: {item.publish_date}</Text>
      </View>

      <Text style={styles.title}>{item.title_ne}</Text>
      {item.title_en ? <Text style={styles.subtitle}>{item.title_en}</Text> : null}

      <Text style={styles.desc} numberOfLines={4}>
        {item.description_ne}
      </Text>

      <View style={styles.cardFooter}>
        {item.attachment ? (
          <TouchableOpacity
            style={styles.attachmentBtn}
            onPress={() => handleDownloadAttachment(item.attachment)}
          >
            <Ionicons name="document-attach" size={14} color={Colors.primary} />
            <Text style={styles.attachmentBtnText}>संलग्न फाइल डाउनलोड</Text>
          </TouchableOpacity>
        ) : (
          <View />
        )}

        <TouchableOpacity
          style={styles.shareBtn}
          onPress={() => handleShareToFeed(item.id)}
        >
          <Ionicons name="share-social" size={14} color={Colors.primaryDark} />
          <Text style={styles.shareBtnText}>फिडमा सेयर</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>विद्यालय सूचना पाटी</Text>
        <Text style={styles.headerSub}>महत्त्वपूर्ण सूचना, निर्देशन तथा सार्वजनिक जानकारी</Text>
      </View>

      {/* Category Filter Pills */}
      <View style={styles.filterBar}>
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={categories}
          keyExtractor={(c) => c}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[
                styles.filterPill,
                selectedCategory === item && { backgroundColor: Colors.primary },
              ]}
              onPress={() => handleCategorySelect(item)}
            >
              <Text
                style={[
                  styles.filterPillText,
                  selectedCategory === item && { color: '#fff', fontWeight: 'bold' },
                ]}
              >
                {item === 'all' ? 'सबै' : item}
              </Text>
            </TouchableOpacity>
          )}
        />
      </View>

      {loading ? (
        <View style={styles.centerLoading}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>सूचनाहरू लोड हुँदैछ...</Text>
        </View>
      ) : (
        <FlatList
          data={filteredNotices}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderNotice}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                loadNotices();
              }}
              colors={[Colors.primary]}
            />
          }
          contentContainerStyle={{ padding: 12, paddingBottom: 24 }}
          ListEmptyComponent={
            <Text style={styles.emptyText}>यो वर्गमा हाल कुनै सूचना उपलब्ध छैन।</Text>
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
  filterBar: { backgroundColor: '#fff', paddingVertical: 10, paddingHorizontal: 12 },
  filterPill: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: '#F1F5F9',
    marginRight: 6,
  },
  filterPillText: { fontSize: 11, color: Colors.textMain },
  centerLoading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  loadingText: { marginTop: 8, fontSize: 12, color: Colors.textMuted },
  card: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  catBadge: {
    backgroundColor: '#EFF6FF',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  catBadgeText: { fontSize: 10, fontWeight: 'bold', color: Colors.primary },
  dateText: { fontSize: 10, color: Colors.textMuted },
  title: { fontSize: 14, fontWeight: 'bold', color: Colors.textMain, marginTop: 4 },
  subtitle: { fontSize: 11, color: Colors.textMuted, marginTop: 1 },
  desc: { fontSize: 12, color: '#334155', lineHeight: 18, marginTop: 6 },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
  },
  attachmentBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  attachmentBtnText: { fontSize: 11, fontWeight: '600', color: Colors.primary },
  shareBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#FEF3C7',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  shareBtnText: { fontSize: 11, fontWeight: 'bold', color: '#B45309' },
  emptyText: { textAlign: 'center', padding: 30, color: Colors.textMuted, fontSize: 12 },
});

