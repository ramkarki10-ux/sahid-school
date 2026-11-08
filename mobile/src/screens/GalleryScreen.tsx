import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  Modal,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../theme/colors';
import { ApiService, API_BASE_URL } from '../services/api';

const { width } = Dimensions.get('window');
const ITEM_SIZE = (width - 36) / 2;

export default function GalleryScreen() {
  const [photos, setPhotos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  const loadGallery = useCallback(async () => {
    try {
      const data = await ApiService.getGallery();
      setPhotos(data.photos || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGallery();
  }, [loadGallery]);

  const getImageUri = (path: string) => {
    if (!path) return 'https://images.unsplash.com/photo-1577896851231-70ef18881754?q=80&w=400';
    if (path.startsWith('http')) return path;
    return `${API_BASE_URL}${path}`;
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>फोटो तथा कार्यक्रम ग्यालरी</Text>
        <Text style={styles.headerSub}>विद्यालयका महत्वपूर्ण कार्यक्रम, खेलकुद तथा उत्सवहरू</Text>
      </View>

      {loading ? (
        <View style={styles.centerLoading}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>तस्बिरहरू लोड हुँदैछ...</Text>
        </View>
      ) : (
        <FlatList
          data={photos}
          numColumns={2}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={{ padding: 12, paddingBottom: 24 }}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.gridItem}
              onPress={() => setSelectedImage(getImageUri(item.photo_url || item.image_path))}
            >
              <Image source={{ uri: getImageUri(item.photo_url || item.image_path) }} style={styles.gridImage} />
              <View style={styles.captionOverlay}>
                <Text style={styles.captionText} numberOfLines={1}>
                  {item.caption || item.title || 'विद्यालय कार्यक्रम'}
                </Text>
              </View>
            </TouchableOpacity>
          )}
          ListEmptyComponent={
            <Text style={styles.emptyText}>हाल कुनै तस्बिरहरू उपलब्ध छैनन्।</Text>
          }
        />
      )}

      {/* Fullscreen Zoom Modal */}
      <Modal visible={!!selectedImage} transparent animationType="fade">
        <View style={styles.modalBg}>
          <TouchableOpacity style={styles.closeBtn} onPress={() => setSelectedImage(null)}>
            <Ionicons name="close" size={28} color="#fff" />
          </TouchableOpacity>
          {selectedImage && (
            <Image source={{ uri: selectedImage }} style={styles.fullImage} resizeMode="contain" />
          )}
        </View>
      </Modal>
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
  gridItem: {
    width: ITEM_SIZE,
    height: ITEM_SIZE,
    margin: 4,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#E2E8F0',
  },
  gridImage: { width: '100%', height: '100%' },
  captionOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingVertical: 4,
    paddingHorizontal: 6,
  },
  captionText: { color: '#fff', fontSize: 10, fontWeight: 'bold' },
  modalBg: { flex: 1, backgroundColor: '#000', alignItems: 'center', justifyContent: 'center' },
  closeBtn: { position: 'absolute', top: 40, right: 20, zIndex: 10, padding: 10 },
  fullImage: { width: '100%', height: '80%' },
  emptyText: { textAlign: 'center', padding: 30, color: Colors.textMuted, fontSize: 12 },
});
