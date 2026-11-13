import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  TouchableOpacity,
  ScrollView,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../theme/colors';
import { useAuth } from '../context/AuthContext';

export default function ProfileScreen() {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    Alert.alert('लगआउट', 'के तपाईं लगआउट गर्न चाहनुहुन्छ?', [
      { text: 'रद्द', style: 'cancel' },
      { text: 'लगआउट', style: 'destructive', onPress: () => logout() },
    ]);
  };

  const roleLabel =
    user?.role === 'SUPER_ADMIN'
      ? 'प्रमुख एडमिन (Super Admin)'
      : user?.role === 'TEACHER'
      ? 'शिक्षक (Teacher)'
      : user?.role === 'STUDENT'
      ? 'विद्यार्थी (Student)'
      : user?.role === 'PARENT'
      ? 'अभिभावक (Parent)'
      : 'प्रयोगकर्ता';

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>प्रयोगकर्ता प्रोफाइल</Text>
        <Text style={styles.headerSub}>सहिद स्मृति डिजिटल परिचयपत्र तथा खाता</Text>
      </View>

      <View style={{ padding: 14 }}>
        {/* Digital School ID Card */}
        <View style={styles.idCard}>
          {/* Card Top Brand */}
          <View style={styles.idCardHeader}>
            <Image
              source={{ uri: 'https://sahid-school.vercel.app/static/images/logo_header.png' }}
              style={styles.cardLogo}
              resizeMode="contain"
            />
            <View style={{ flex: 1, marginLeft: 8 }}>
              <Text style={styles.cardSchoolName}>सहिद स्मृति आवासीय मा.वि.</Text>
              <Text style={styles.cardSchoolSub}>इटहरी-१९, सुनसरी • डिजिटल परिचयपत्र</Text>
            </View>
          </View>

          {/* User Photo & Main Info */}
          <View style={styles.cardBody}>
            <Image
              source={{
                uri:
                  user?.avatar ||
                  `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.username || 'User')}&background=1B365D&color=fff`,
              }}
              style={styles.cardAvatar}
            />
            <View style={{ flex: 1, marginLeft: 14 }}>
              <Text style={styles.cardName}>{user?.full_name_ne || user?.username}</Text>
              <View style={styles.cardRoleBadge}>
                <Text style={styles.cardRoleText}>{roleLabel}</Text>
              </View>
              <Text style={styles.cardField}>
                युजरनेम: <Text style={styles.cardFieldVal}>{user?.username}</Text>
              </Text>
              {user?.phone ? (
                <Text style={styles.cardField}>
                  सम्पर्क: <Text style={styles.cardFieldVal}>{user?.phone}</Text>
                </Text>
              ) : null}
            </View>
          </View>

          {/* Bottom Bar / Barcode simulation */}
          <View style={styles.cardFooter}>
            <Text style={styles.cardStatusText}>● खाता स्थिति: सक्रिय (ACTIVE)</Text>
            <View style={styles.barcodeSim}>
              <Text style={{ fontFamily: 'monospace', fontSize: 10, letterSpacing: 2, color: Colors.primary }}>
                |||| | ||||| || |||||| |
              </Text>
            </View>
          </View>
        </View>

        {/* Menu Options */}
        <View style={styles.menuCard}>
          <TouchableOpacity
            style={styles.menuItem}
            onPress={() => (navigation as any).navigate('Administration')}
          >
            <Ionicons name="business-outline" size={20} color={Colors.primary} />
            <Text style={styles.menuText}>विद्यालय प्रशासन (व्यवस्थापन, गुठियार र शिक्षकहरू)</Text>
            <Ionicons name="chevron-forward" size={16} color={Colors.textMuted} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <Ionicons name="shield-checkmark-outline" size={20} color={Colors.primary} />
            <Text style={styles.menuText}>खाता सुरक्षा तथा पासवर्ड</Text>
            <Ionicons name="chevron-forward" size={16} color={Colors.textMuted} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <Ionicons name="notifications-outline" size={20} color={Colors.primary} />
            <Text style={styles.menuText}>सूचना तथा नोटिफिकेसन सेटिङ</Text>
            <Ionicons name="chevron-forward" size={16} color={Colors.textMuted} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <Ionicons name="help-circle-outline" size={20} color={Colors.primary} />
            <Text style={styles.menuText}>विद्यालय सहायता तथा सम्पर्क</Text>
            <Ionicons name="chevron-forward" size={16} color={Colors.textMuted} />
          </TouchableOpacity>
        </View>

        {/* Logout Button */}
        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={18} color="#DC2626" />
          <Text style={styles.logoutBtnText}>खाताबाट लगआउट गर्नुहोस्</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
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
  idCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    borderWidth: 2,
    borderColor: Colors.gold,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  idCardHeader: {
    backgroundColor: Colors.primary,
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
  },
  cardLogo: { width: 30, height: 30 },
  cardSchoolName: { color: '#fff', fontSize: 13, fontWeight: 'bold' },
  cardSchoolSub: { color: Colors.gold, fontSize: 9 },
  cardBody: { flexDirection: 'row', alignItems: 'center', padding: 14 },
  cardAvatar: {
    width: 65,
    height: 65,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#CBD5E1',
  },
  cardName: { fontSize: 14, fontWeight: 'bold', color: Colors.textMain },
  cardRoleBadge: {
    backgroundColor: '#EFF6FF',
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    marginVertical: 4,
  },
  cardRoleText: { fontSize: 10, fontWeight: 'bold', color: Colors.primary },
  cardField: { fontSize: 11, color: Colors.textMuted, marginTop: 1 },
  cardFieldVal: { fontWeight: '600', color: Colors.textMain },
  cardFooter: {
    backgroundColor: '#F8FAFC',
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    paddingHorizontal: 14,
    paddingVertical: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  cardStatusText: { fontSize: 10, color: Colors.success, fontWeight: 'bold' },
  barcodeSim: { backgroundColor: '#fff', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  menuCard: {
    backgroundColor: '#fff',
    borderRadius: 14,
    marginTop: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  menuText: { flex: 1, marginLeft: 10, fontSize: 12, fontWeight: '600', color: Colors.textMain },
  logoutBtn: {
    backgroundColor: '#FEE2E2',
    borderWidth: 1,
    borderColor: '#FCA5A5',
    borderRadius: 12,
    paddingVertical: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 16,
  },
  logoutBtnText: { color: '#DC2626', fontSize: 13, fontWeight: 'bold' },
});

