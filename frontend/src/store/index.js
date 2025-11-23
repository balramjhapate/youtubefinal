import { create } from 'zustand';

export const useStore = create((set, get) => ({
  // Selected videos for bulk operations
  selectedVideos: [],

  toggleVideoSelection: (id) => {
    const { selectedVideos } = get();
    if (selectedVideos.includes(id)) {
      set({ selectedVideos: selectedVideos.filter((vid) => vid !== id) });
    } else {
      set({ selectedVideos: [...selectedVideos, id] });
    }
  },

  selectAllVideos: (ids) => {
    set({ selectedVideos: ids });
  },

  clearSelection: () => {
    set({ selectedVideos: [] });
  },

  // Sidebar state
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  // Settings modal
  settingsModalOpen: false,
  openSettingsModal: () => set({ settingsModalOpen: true }),
  closeSettingsModal: () => set({ settingsModalOpen: false }),

  // Video detail modal
  videoDetailModalOpen: false,
  selectedVideoId: null,
  openVideoDetail: (id) => set({ videoDetailModalOpen: true, selectedVideoId: id }),
  closeVideoDetail: () => set({ videoDetailModalOpen: false, selectedVideoId: null }),
}));

export default useStore;
