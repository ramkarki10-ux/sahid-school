import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  TextInput,
  ActivityIndicator,
  RefreshControl,
  Linking,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../theme/colors';
import { ApiService, resolveImageUrl, DEFAULT_AVATAR } from '../services/api';

type TabType = 'smc' | 'guthiyar' | 'teachers' | 'leadership';

export default function AdministrationScreen() {
  const [activeTab, setActiveTab] = useState<TabType>('smc');
  const [smcList, setSmcList] = useState<any[]>([]);
  const [guthiyarList, setGuthiyarList] = useState<any[]>([]);
  const [teachersList, setTeachersList] = useState<any[]>([]);
  const [leadershipList, setLeadershipList] = useState<any[]>([]);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const [imageErrors, setImageErrors] = useState<{ [key: string]: boolean }>({});

  const fetchAdminData = useCallback(async (isPullToRefresh = false) => {
    if (isPullToRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      // Pass forceRefresh: true to bypass cache on pull-to-refresh
      const data = await ApiService.getAdministration(isPullToRefresh);
      if (data && data.success) {
        setSmcList(data.smc || []);
        setGuthiyarList(data.guthiyar || []);
        setTeachersList(data.teachers || []);
        setLeadershipList(data.leadership || []);
        
        const now = new Date();
        const timeStr = now.toLocaleTimeString('ne-NP', { hour: '2-digit', minute: '2-digit' });
        setLastUpdated(`अन्तिम अद्यावधिक: आज ${timeStr}`);
      }
    } catch (e) {
      console.error('Failed to load administration data:', e);
      Alert.alert(
        'डेटा लोड हुन सकेन',
        'सर्भरसँग सम्पर्क हुन सकेन। कृपया इन्टरनेट जाँच्नुहोस् वा पुनः प्रयास गर्नुहोस्।'
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAdminData();
  }, [fetchAdminData]);

  // Handle explicit cache clear and refresh
  const handleClearCacheAndRefresh = () => {
    setImageErrors({});
    fetchAdminData(true);
  };

  // Get active list based on selected tab
  const getActiveList = () => {
    let list: any[] = [];
    if (activeTab === 'smc') list = smcList;
    else if (activeTab === 'guthiyar') list = guthiyarList;
    else if (activeTab === 'teachers') list = teachersList;
    else if (activeTab === 'leadership') list = leadershipList;

    if (!searchQuery.trim()) return list;

    const q = searchQuery.trim().toLowerCase();
    return list.filter((item) => {
      const name = (item.name || item.name_nepali || item.name_english || '').toLowerCase();
      const pos = (item.position || item.designation || '').toLowerCase();
      const sub = (item.subject || '').toLowerCase();
      const qual = (item.qualification || '').toLowerCase();
      return name.includes(q) || pos.includes(q) || sub.includes(q) || qual.includes(q);
    });
  };

  const handleCall = (phone?: string) => {
    if (!phone) {
      Alert.alert('सम्पर्क नम्बर उपलब्ध छैन', 'यो व्यक्तिको फोन नम्बर दर्ता गरिएको छैन।');
      return;
    }
    Linking.openURL(`tel:${phone.replace(/\s+/g, '')}`).catch(() => {
      Alert.alert('कल गर्न सकिएन', phone);
    });
  };

  const handleEmail = (email?: string) => {
    if (!email) {
      Alert.alert('इमेल उपलब्ध छैन', 'यो व्यक्तिको इमेल ठेगाना दर्ता गरिएको छैन।');
      return;
    }
    Linking.openURL(`mailto:${email.trim()}`).catch(() => {
      Alert.alert('इमेल खोल्न सकिएन', email);
    });
  };

  const renderMemberCard = ({ item, index }: { item: any; index: number }) => {
    const rawPhoto = item.photo || item.avatar_url;
    const resolvedUrl = resolveImageUrl(rawPhoto);
    const itemKey = `${activeTab}_${item.id || index}`;
    const hasImageError = imageErrors[itemKey];

    const name = item.name_nepali || item.name || item.name_english || 'नाम उपलब्ध छैन';
    const designation = item.position || item.designation || (activeTab === 'teachers' ? 'शिक्षक' : 'सदस्य');
    const qualification = item.qualification;
    const experience = item.experience;
    const subject = item.subject;
    const level = item.level;
    const address = item.address;
    const phone = item.phone;
    const email = item.email;
    const term = item.term;

    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          {/* Avatar with Error Fallback */}
          <View style={styles.avatarWrapper}>
            {!hasImageError && resolvedUrl && resolvedUrl !== DEFAULT_AVATAR ? (
              <Image
                source={{ uri: resolvedUrl }}
                style={styles.avatar}
                resizeMode="cover"
                onError={() => {
                  setImageErrors((prev) => ({ ...prev, [itemKey]: true }));
                }}
              />
            ) : (
              <View style={[styles.avatar, styles.fallbackAvatar]}>
                <Ionicons
                  name={activeTab === 'teachers' ? 'school' : 'person'}
                  size={32}
                  color={Colors.primary}
                />
              </View>
            )}
            <View style={styles.statusIndicator} />
          </View>

          {/* Core Info */}
          <View style={styles.infoCol}>
            <View style={styles.designationBadge}>
              <Text style={styles.designationText}>{designation}</Text>
            </View>
            <Text style={styles.nameText}>{name}</Text>
            {item.name_english ? (
              <Text style={styles.englishNameText}>{item.name_english}</Text>
            ) : null}
            {term ? <Text style={styles.termText}>पदावधि: {term}</Text> : null}
          </View>
        </View>

        {/* Detailed Metadata Attributes */}
        <View style={styles.detailsSection}>
          {qualification ? (
            <View style={styles.detailRow}>
              <Ionicons name="ribbon-outline" size={14} color={Colors.gold} style={styles.detailIcon} />
              <Text style={styles.detailLabel}>योग्यता:</Text>
              <Text style={styles.detailValue} numberOfLines={2}>
                {qualification}
              </Text>
            </View>
          ) : null}

          {experience ? (
            <View style={styles.detailRow}>
              <Ionicons name="time-outline" size={14} color="#6366F1" style={styles.detailIcon} />
              <Text style={styles.detailLabel}>अनुभव:</Text>
              <Text style={styles.detailValue}>{experience}</Text>
            </View>
          ) : null}

          {subject ? (
            <View style={styles.detailRow}>
              <Ionicons name="book-outline" size={14} color="#059669" style={styles.detailIcon} />
              <Text style={styles.detailLabel}>विषय / तह:</Text>
              <Text style={styles.detailValue}>
                {subject} {level ? `(${level})` : ''}
              </Text>
            </View>
          ) : null}

          {address ? (
            <View style={styles.detailRow}>
              <Ionicons name="location-outline" size={14} color="#EF4444" style={styles.detailIcon} />
              <Text style={styles.detailLabel}>ठेगाना:</Text>
              <Text style={styles.detailValue}>{address}</Text>
            </View>
          ) : null}
        </View>

        {/* Quick Contact Action Buttons */}
        <View style={styles.actionsRow}>
          {phone ? (
            <TouchableOpacity
              style={[styles.contactBtn, styles.callBtn]}
              onPress={() => handleCall(phone)}
              activeOpacity={0.8}
            >
              <Ionicons name="call" size={13} color="#FFFFFF" />
              <Text style={styles.contactBtnText}>{phone}</Text>
            </TouchableOpacity>
          ) : null}

          {email ? (
            <TouchableOpacity
              style={[styles.contactBtn, styles.emailBtn]}
              onPress={() => handleEmail(email)}
              activeOpacity={0.8}
            >
              <Ionicons name="mail" size={13} color={Colors.primary} />
              <Text style={[styles.contactBtnText, { color: Colors.primary }]} numberOfLines={1}>
                इमेल
              </Text>
            </TouchableOpacity>
          ) : null}
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {/* Top Header */}
      <View style={styles.header}>
        <View style={styles.headerTitleRow}>
          <View>
            <Text style={styles.headerTitle}>विद्यालय प्रशासन</Text>
            <Text style={styles.headerSubtitle}>
              समिति तथा शिक्षकशिक्षिका विवरण (School Administration)
            </Text>
          </View>
          <TouchableOpacity
            style={styles.refreshIconBtn}
            onPress={handleClearCacheAndRefresh}
            activeOpacity={0.7}
          >
            <Ionicons name="refresh" size={18} color="#FFFFFF" />
          </TouchableOpacity>
        </View>

        {lastUpdated ? (
          <Text style={styles.lastUpdatedText}>{lastUpdated}</Text>
        ) : null}

        {/* Search Bar */}
        <View style={styles.searchBox}>
          <Ionicons name="search" size={16} color={Colors.textMuted} style={{ marginRight: 6 }} />
          <TextInput
            style={styles.searchInput}
            placeholder="नाम, पद वा विषय खोज्नुहोस्..."
            placeholderTextColor="#94A3B8"
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
          {searchQuery ? (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Ionicons name="close-circle" size={16} color={Colors.textMuted} />
            </TouchableOpacity>
          ) : null}
        </View>

        {/* Segmented Navigation Tabs */}
        <View style={styles.tabsRow}>
          <TouchableOpacity
            style={[styles.tabBtn, activeTab === 'smc' && styles.activeTabBtn]}
            onPress={() => setActiveTab('smc')}
          >
            <Ionicons
              name="people"
              size={13}
              color={activeTab === 'smc' ? '#FFFFFF' : Colors.textMuted}
            />
            <Text style={[styles.tabBtnText, activeTab === 'smc' && styles.activeTabBtnText]}>
              व्यवस्थापन समिति ({smcList.length})
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tabBtn, activeTab === 'guthiyar' && styles.activeTabBtn]}
            onPress={() => setActiveTab('guthiyar')}
          >
            <Ionicons
              name="business"
              size={13}
              color={activeTab === 'guthiyar' ? '#FFFFFF' : Colors.textMuted}
            />
            <Text style={[styles.tabBtnText, activeTab === 'guthiyar' && styles.activeTabBtnText]}>
              गुठियार समिति ({guthiyarList.length})
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tabBtn, activeTab === 'teachers' && styles.activeTabBtn]}
            onPress={() => setActiveTab('teachers')}
          >
            <Ionicons
              name="school"
              size={13}
              color={activeTab === 'teachers' ? '#FFFFFF' : Colors.textMuted}
            />
            <Text style={[styles.tabBtnText, activeTab === 'teachers' && styles.activeTabBtnText]}>
              शिक्षकशिक्षिका ({teachersList.length})
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tabBtn, activeTab === 'leadership' && styles.activeTabBtn]}
            onPress={() => setActiveTab('leadership')}
          >
            <Ionicons
              name="medal"
              size={13}
              color={activeTab === 'leadership' ? '#FFFFFF' : Colors.textMuted}
            />
            <Text style={[styles.tabBtnText, activeTab === 'leadership' && styles.activeTabBtnText]}>
              नेतृत्व ({leadershipList.length})
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Content List */}
      {loading ? (
        <View style={styles.loadingBox}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>विवरणहरू लोड हुँदैछन्...</Text>
        </View>
      ) : (
        <FlatList
          data={getActiveList()}
          keyExtractor={(item, index) => `${activeTab}_${item.id || index}`}
          renderItem={renderMemberCard}
          contentContainerStyle={styles.listContainer}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => fetchAdminData(true)}
              colors={[Colors.primary]}
              tintColor={Colors.primary}
            />
          }
          ListEmptyComponent={
            <View style={styles.emptyBox}>
              <Ionicons name="information-circle-outline" size={42} color="#94A3B8" />
              <Text style={styles.emptyText}>कुनै पनि विवरण फेला परेन।</Text>
              <TouchableOpacity style={styles.emptyRefreshBtn} onPress={handleClearCacheAndRefresh}>
                <Text style={styles.emptyRefreshText}>पुनः लोड गर्नुहोस्</Text>
              </TouchableOpacity>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  header: {
    backgroundColor: Colors.primary,
    paddingTop: 48,
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 4,
  },
  headerTitleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: -0.3,
  },
  headerSubtitle: {
    fontSize: 11,
    color: '#CBD5E1',
    marginTop: 2,
  },
  refreshIconBtn: {
    padding: 8,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 10,
  },
  lastUpdatedText: {
    fontSize: 10,
    color: Colors.gold,
    marginTop: 4,
    fontWeight: '600',
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 10,
    height: 38,
    marginTop: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 12,
    color: Colors.textMain,
    paddingVertical: 0,
  },
  tabsRow: {
    flexDirection: 'row',
    marginTop: 10,
    backgroundColor: 'rgba(0,0,0,0.2)',
    borderRadius: 12,
    padding: 3,
    gap: 4,
  },
  tabBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 7,
    paddingHorizontal: 4,
    borderRadius: 9,
    gap: 3,
  },
  activeTabBtn: {
    backgroundColor: Colors.primaryLight,
  },
  tabBtnText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#CBD5E1',
  },
  activeTabBtnText: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  listContainer: {
    padding: 14,
    paddingBottom: 30,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 1.5 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  avatarWrapper: {
    position: 'relative',
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#F1F5F9',
    borderWidth: 2,
    borderColor: '#CBD5E1',
  },
  fallbackAvatar: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#E0E7FF',
    borderColor: '#818CF8',
  },
  statusIndicator: {
    position: 'absolute',
    bottom: 2,
    right: 2,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#10B981',
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  infoCol: {
    flex: 1,
  },
  designationBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#FEF3C7',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    marginBottom: 3,
  },
  designationText: {
    fontSize: 10,
    fontWeight: '800',
    color: '#92400E',
    textTransform: 'uppercase',
  },
  nameText: {
    fontSize: 15,
    fontWeight: '800',
    color: Colors.textMain,
    lineHeight: 20,
  },
  englishNameText: {
    fontSize: 11,
    color: Colors.textMuted,
    fontStyle: 'italic',
  },
  termText: {
    fontSize: 10,
    color: Colors.textMuted,
    marginTop: 2,
  },
  detailsSection: {
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
    gap: 4,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  detailIcon: {
    marginRight: 2,
  },
  detailLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#64748B',
  },
  detailValue: {
    fontSize: 11,
    fontWeight: '500',
    color: '#1E293B',
    flex: 1,
  },
  actionsRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
  },
  contactBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 7,
    paddingHorizontal: 10,
    borderRadius: 10,
    gap: 6,
  },
  callBtn: {
    backgroundColor: '#059669',
  },
  emailBtn: {
    backgroundColor: '#EEF2FF',
    borderWidth: 1,
    borderColor: '#C7D2FE',
  },
  contactBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  loadingBox: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  loadingText: {
    fontSize: 12,
    color: Colors.textMuted,
    fontWeight: '600',
  },
  emptyBox: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 50,
    gap: 8,
  },
  emptyText: {
    fontSize: 13,
    color: Colors.textMuted,
  },
  emptyRefreshBtn: {
    paddingVertical: 6,
    paddingHorizontal: 14,
    backgroundColor: Colors.primary,
    borderRadius: 8,
  },
  emptyRefreshText: {
    fontSize: 11,
    color: '#FFFFFF',
    fontWeight: '700',
  },
});

