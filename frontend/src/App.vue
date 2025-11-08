<template>
  <div id="app">
    <el-container>
      <el-header class="header">
        <div class="header-content">
          <h2>
            数据标注系统
          </h2>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <!-- 上传区域 -->
        <div v-if="!currentFilename" class="upload-section">
          <!-- 文件列表 -->
          <el-card class="files-card">
            <template #header>
              <div class="files-header">
                <h3>
                  <el-icon><Folder /></el-icon>
                  文件列表
                  <el-tag v-if="fileList.length > 0" type="info" size="small" style="margin-left: 10px;">
                    {{ fileList.length }} 个文件
                  </el-tag>
                </h3>
                <div class="header-actions">
                  <el-button @click="showUploadDialog" size="small" type="primary">
                    <el-icon><UploadFilled /></el-icon>
                    上传文件
                  </el-button>
                  <el-button @click="refreshFileList" size="small" type="primary" plain>
                    <el-icon><Refresh /></el-icon>
                    刷新
                  </el-button>
                </div>
              </div>
            </template>
            
            <div v-if="fileList.length === 0" class="empty-files">
              <el-empty description="暂无文件，点击上传按钮添加文件">
                <el-button @click="showUploadDialog" type="primary">
                  <el-icon><UploadFilled /></el-icon>
                  上传第一个文件
                </el-button>
              </el-empty>
            </div>
            
            <el-table v-else :data="fileList" style="width: 100%" v-loading="filesLoading">
              <el-table-column prop="original_filename" label="文件名" min-width="100">
                <template #default="scope">
                  <div class="filename-cell">
                    <el-icon><Document /></el-icon>
                    <span>{{ scope.row.original_filename }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="标注类型" width="120">
                <template #default="scope">
                  <el-tag v-if="scope.row.annotation_type === 'qa'" type="success" size="small">
                    QA标注
                  </el-tag>
                  <el-tag v-else-if="scope.row.annotation_type === 'scoring'" type="warning" size="small">
                    评分标注
                  </el-tag>
                  <el-tag v-else type="info" size="small">
                    未知
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="file_size_formatted" label="文件大小" width="120" />
              <el-table-column prop="total_records" label="记录数" width="100" />
              <el-table-column prop="upload_time" label="上传时间" width="180">
                <template #default="scope">
                  {{ formatDateTime(scope.row.upload_time) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200">
                <template #default="scope">
                  <el-button 
                    @click="openFile(scope.row.filename)" 
                    size="small" 
                    type="primary"
                  >
                    打开
                  </el-button>
                  <el-button 
                    @click="deleteFile(scope.row.filename)" 
                    size="small" 
                    type="danger"
                    plain
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>

        <!-- 主要内容区域 -->
        <div v-else class="data-section">
          <!-- 文件信息和返回按钮 -->
          <el-card class="file-info-card">
            <div class="file-info-header">
              <div class="file-info">
                <h2>
                  <el-icon><Document /></el-icon>
                  当前标注文件：{{ getCurrentFileName() }}
                  <el-tag v-if="currentAnnotationType === 'qa'" type="success" size="large" style="margin-left: 12px;">
                    QA标注
                  </el-tag>
                  <el-tag v-else-if="currentAnnotationType === 'scoring'" type="warning" size="large" style="margin-left: 12px;">
                    评分标注
                  </el-tag>
                </h2>
              </div>
              <el-button @click="backToHome" type="primary" size="large">
                <el-icon><ArrowLeft /></el-icon>
                返回主页
              </el-button>
            </div>
          </el-card>

          <!-- 统计信息 -->
          <el-row :gutter="20" class="stats-row">
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-content">
                  <div class="stat-number">{{ stats.total_count }}</div>
                  <div class="stat-label">总数据量</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card correct">
                <div class="stat-content">
                  <div class="stat-number">{{ stats.correct_count }}</div>
                  <div class="stat-label">{{ currentAnnotationType === 'scoring' ? '优质' : '正确' }}</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card incorrect">
                <div class="stat-content">
                  <div class="stat-number">{{ stats.incorrect_count }}</div>
                  <div class="stat-label">{{ currentAnnotationType === 'scoring' ? '劣质' : '错误' }}</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card unannotated">
                <div class="stat-content">
                  <div class="stat-number">{{ stats.unannotated_count }}</div>
                  <div class="stat-label">未标注</div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 筛选和控制区域 -->
          <el-card class="filter-card">
            <div class="filter-row">
              <div class="filter-left">
                <div class="filter-item horizontal">
                  <div class="filter-label">筛选状态</div>
                  <el-select 
                    v-model="filters.annotation_status" 
                    placeholder="标注状态" 
                    @change="applyFilters"
                    style="width: 120px;"
                  >
                    <el-option label="全部" value="all" />
                    <el-option label="已标注" value="annotated" />
                    <el-option label="未标注" value="not_annotated" />
                  </el-select>
                </div>
                <div class="filter-item horizontal">
                  <div class="filter-label">显示数量</div>
                  <el-select 
                    v-model="filters.per_page" 
                    @change="applyFilters"
                    style="width: 100px;"
                  >
                    <el-option label="10条" :value="10" />
                    <el-option label="20条" :value="20" />
                    <el-option label="50条" :value="50" />
                    <el-option label="100条" :value="100" />
                  </el-select>
                </div>
              </div>
              <div class="filter-right">
                <div class="filter-item horizontal">
                  <el-button 
                    type="success" 
                    size="default"
                    @click="showExportDialog"
                    :loading="exporting"
                  >
                    <el-icon><Download /></el-icon>
                    导出数据
                  </el-button>
                </div>
              </div>
            </div>
          </el-card>

          <!-- 数据列表 -->
          <el-card class="data-card">
            <div v-loading="loading" class="data-list">
              <div v-if="dataList.length === 0" class="no-data">
                <el-empty description="没有找到匹配的数据" />
              </div>
              <div v-else>
                <div
                  v-for="item in dataList"
                  :key="item.unique_id"
                  class="data-item"
                  :class="{ 
                    selected: item.selected,
                    'hiding': item.isHiding,
                    'annotated-correct': item.annotation_result === 'correct',
                    'annotated-incorrect': item.annotation_result === 'incorrect'
                  }"
                >
                  <div class="data-header">
                    <el-tag type="info">#{{ item.line_number }}</el-tag>
                    <div class="data-controls">
                      <div class="annotation-selector" v-if="!item.annotation_result">
                        <span>标注:</span>
                        <!-- QA标注 -->
                        <el-radio-group 
                          v-if="currentAnnotationType === 'qa'"
                          @change="(value) => annotateItem(item.unique_id, value)"
                        >
                          <el-radio value="correct">正确</el-radio>
                          <el-radio value="incorrect">错误</el-radio>
                        </el-radio-group>
                        <!-- 评分标注 -->
                        <div v-else-if="currentAnnotationType === 'scoring'" class="scoring-selector">
                          <el-rate 
                            v-model="item.tempScore"
                            :max="5"
                            show-score
                            text-color="#ff9900"
                            score-template="{value} 分"
                            @change="(value) => annotateItem(item.unique_id, value.toString())"
                          />
                          <el-button 
                            v-if="item.tempScore"
                            type="primary" 
                            size="small"
                            @click="annotateItem(item.unique_id, item.tempScore.toString())"
                          >
                            确认评分
                          </el-button>
                        </div>
                      </div>
                      <div class="annotation-result" v-else>
                        <!-- QA标注结果 -->
                        <el-tag 
                          v-if="currentAnnotationType === 'qa'"
                          :type="item.annotation_result === 'correct' ? 'success' : 'danger'"
                          size="large"
                        >
                          {{ item.annotation_result === 'correct' ? '✓ 正确' : '✗ 错误' }}
                        </el-tag>
                        <!-- 评分标注结果 -->
                        <el-tag 
                          v-else-if="currentAnnotationType === 'scoring'"
                          type="warning"
                          size="large"
                        >
                          {{ item.annotation_result }} 分
                        </el-tag>
                      </div>
                    </div>
                  </div>
                  <div class="data-content">
                    <div class="data-field">
                      <div class="field-label">System</div>
                      <div class="field-content">{{ item.system || '' }}</div>
                    </div>
                    <div class="data-field">
                      <div class="field-label">Query</div>
                      <div class="field-content">{{ item.query || '' }}</div>
                    </div>
                    <div class="data-field">
                      <div class="field-label">Response</div>
                      <div class="field-content">{{ item.response || '' }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 分页 -->
            <div class="pagination">
              <el-pagination
                v-model:current-page="pagination.page"
                v-model:page-size="pagination.per_page"
                :page-sizes="[10, 20, 50, 100]"
                :total="pagination.total_count"
                layout="total, sizes, prev, pager, next, jumper"
                @size-change="handlePageSizeChange"
                @current-change="handlePageChange"
              />
            </div>
          </el-card>
        </div>
      </el-main>
    </el-container>


    <!-- 上传文件对话框 -->
    <el-dialog 
      v-model="uploadDialog.visible" 
      title="上传文件" 
      width="500px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="simple-upload-dialog"
    >
      <div class="simple-upload-form">
        <!-- 标注类型选择 -->
        <div class="form-section">
          <h4>标注类型</h4>
          <el-radio-group v-model="uploadDialog.annotationType">
            <el-radio value="qa">QA标注（正确/错误）</el-radio>
            <el-radio value="scoring">评分标注（1-5分）</el-radio>
          </el-radio-group>
        </div>

        <!-- 文件上传 -->
        <div class="form-section">
          <h4>选择文件</h4>
          <el-upload
            class="simple-upload"
            drag
            :auto-upload="false"
            :on-change="handleFileChangeInDialog"
            :show-file-list="false"
            accept=".jsonl"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                仅支持 .jsonl 格式文件
              </div>
            </template>
          </el-upload>
        </div>
      </div>
      
      <div v-if="uploadDialog.uploading" class="simple-upload-progress">
        <el-progress :percentage="uploadDialog.progress" />
        <p style="margin-top: 8px; font-size: 14px; color: #666;">
          {{ uploadDialog.statusText }}
        </p>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button 
            @click="uploadDialog.visible = false" 
            :disabled="uploadDialog.uploading"
          >
            取消
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 导出数据对话框 -->
    <el-dialog 
      v-model="exportDialog.visible" 
      title="导出数据" 
      width="450px"
      class="simple-export-dialog"
    >
      <div class="simple-export-form">
        <div class="form-section">
          <h4>数据统计</h4>
          <div class="export-stats">
            <div class="stat-item">
              <span>{{ currentAnnotationType === 'scoring' ? '优质数据：' : '正确数据：' }}</span>
              <span class="stat-value correct">{{ stats.correct_count }} 条</span>
            </div>
            <div class="stat-item">
              <span>{{ currentAnnotationType === 'scoring' ? '劣质数据：' : '错误数据：' }}</span>
              <span class="stat-value incorrect">{{ stats.incorrect_count }} 条</span>
            </div>
          </div>
        </div>
        
        <div class="form-section">
          <h4>导出类型</h4>
          <el-radio-group v-model="exportDialog.selectedType">
            <el-radio value="correct" :disabled="stats.correct_count === 0">
              {{ currentAnnotationType === 'scoring' ? '导出优质数据' : '导出正确数据' }}
            </el-radio>
            <el-radio value="incorrect" :disabled="stats.incorrect_count === 0">
              {{ currentAnnotationType === 'scoring' ? '导出劣质数据' : '导出错误数据' }}
            </el-radio>
          </el-radio-group>
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="exportDialog.visible = false">取消</el-button>
          <el-button 
            type="primary" 
            @click="confirmExport"
            :disabled="!exportDialog.selectedType"
            :loading="exporting"
          >
            确认导出
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Folder, UploadFilled, Refresh, Document, ArrowLeft, Download, 
  Setting, Check, Star, Upload, InfoFilled, Loading 
} from '@element-plus/icons-vue'
import axios from 'axios'
// 简单的防抖函数实现
const debounce = (func, wait) => {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

export default {
  name: 'App',
  setup() {
    // 响应式数据
    const loading = ref(false)
    const currentFilename = ref('')
    const currentAnnotationType = ref('qa')  // 当前文件的标注类型
    const dataList = ref([])
    const stats = reactive({
      total_count: 0,
      correct_count: 0,
      incorrect_count: 0,
      unannotated_count: 0,
      avg_quality: 0
    })
    
    const filters = reactive({
      search: '',
      annotation_status: 'not_annotated',
      selected_only: false,
      per_page: 10
    })
    
    const pagination = reactive({
      page: 1,
      per_page: 20,
      total_count: 0,
      total_pages: 0
    })
    

    // 文件列表相关
    const fileList = ref([])
    const filesLoading = ref(false)

    // 上传对话框相关
    const uploadDialog = reactive({
      visible: false,
      uploading: false,
      progress: 0,
      statusText: '',
      annotationType: 'qa'  // 默认选择QA标注
    })

    // 导出相关
    const exporting = ref(false)
    const exportType = ref('correct')  // 默认导出正确的数据
    
    // 导出对话框相关
    const exportDialog = reactive({
      visible: false,
      selectedType: 'correct'
    })

    // 文件上传处理
    const handleFileChange = async (file) => {
      if (!file.raw.name.endsWith('.jsonl')) {
        ElMessage.error('请上传JSONL格式的文件')
        return
      }
      
      loading.value = true
      
      try {
        const formData = new FormData()
        formData.append('file', file.raw)
        
        const response = await axios.post('/api/upload', formData)
        
        if (response.data) {
          currentFilename.value = response.data.filename
          ElMessage.success(`文件上传成功，共 ${response.data.total_count} 条数据`)
          await loadData()
          await loadStats()
        }
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '上传失败')
      } finally {
        loading.value = false
      }
    }

    // 加载数据
    const loadData = async () => {
      if (!currentFilename.value) return
      
      loading.value = true
      
      try {
        const params = {
          filename: currentFilename.value,
          search: filters.search,
          annotation_status: filters.annotation_status,
          selected_only: filters.selected_only,
          page: pagination.page,
          per_page: filters.per_page
        }
        
        const response = await axios.get('/api/data', { params })
        
        if (response.data) {
          dataList.value = response.data.data
          pagination.total_count = response.data.total_count
          pagination.total_pages = response.data.total_pages
          pagination.per_page = response.data.per_page
        }
      } catch (error) {
        ElMessage.error('加载数据失败')
      } finally {
        loading.value = false
      }
    }

    // 加载统计信息
    const loadStats = async () => {
      if (!currentFilename.value) return
      
      try {
        const response = await axios.get(`/api/stats/${currentFilename.value}`)
        
        if (response.data) {
          Object.assign(stats, response.data)
        }
      } catch (error) {
        console.error('加载统计信息失败:', error)
      }
    }

    // 应用筛选
    const applyFilters = async () => {
      // 同步筛选器和分页的每页数量
      pagination.per_page = filters.per_page
      // 只有在当前不是第一页时才重置页码
      if (pagination.page !== 1) {
        pagination.page = 1
      }
      await loadData()
    }

    // 防抖搜索
    const debounceSearch = debounce(applyFilters, 300)

    // 处理分页组件的大小变化
    const handlePageSizeChange = async (newPageSize) => {
      filters.per_page = newPageSize
      pagination.per_page = newPageSize
      pagination.page = 1  // 改变页面大小时重置到第一页
      await loadData()
    }

    // 处理分页组件的页码变化
    const handlePageChange = async (newPage) => {
      pagination.page = newPage
      await loadData()
    }

    // 更新数据项
    const updateItem = async (lineNumber, updates) => {
      try {
        await axios.post('/api/update', {
          filename: currentFilename.value,
          line_number: lineNumber,
          updates: updates
        })
        
        await loadStats()
      } catch (error) {
        ElMessage.error('更新失败')
      }
    }

    // 标注数据并自动隐藏
    const annotateItem = async (uniqueId, annotationResult) => {
      try {
        await axios.post('/api/annotate', {
          unique_id: uniqueId,
          annotation_result: annotationResult
        })
        
        // 从当前列表中移除已标注的项目
        const index = dataList.value.findIndex(item => item.unique_id === uniqueId)
        if (index !== -1) {
          // 添加消失动画
          const item = dataList.value[index]
          item.isHiding = true
          
          // 延迟移除以显示动画
          setTimeout(() => {
            dataList.value.splice(index, 1)
            // 更新统计信息
            loadStats()
          }, 300)
        } else {
          // 如果不在当前列表中，直接更新统计信息
          await loadStats()
        }
        
        ElMessage.success('标注成功')
      } catch (error) {
        ElMessage.error('标注失败')
      }
    }

    // 获取当前文件名
    const getCurrentFileName = () => {
      if (!currentFilename.value) return ''
      const file = fileList.value.find(f => f.filename === currentFilename.value)
      return file ? file.original_filename : currentFilename.value
    }

    // 返回主页
    const backToHome = () => {
      currentFilename.value = ''
      dataList.value = []
      Object.assign(stats, {
        total_count: 0,
        correct_count: 0,
        incorrect_count: 0,
        unannotated_count: 0,
        avg_quality: 0
      })
      Object.assign(filters, {
        search: '',
        annotation_status: 'not_annotated',
        selected_only: false,
        per_page: 10
      })
      Object.assign(pagination, {
        page: 1,
        per_page: 10,
        total_count: 0,
        total_pages: 0
      })
    }

    // 文件列表相关功能
    const loadFileList = async () => {
      filesLoading.value = true
      try {
        const response = await axios.get('/api/files')
        if (response.data) {
          fileList.value = response.data.files
        }
      } catch (error) {
        ElMessage.error('加载文件列表失败')
      } finally {
        filesLoading.value = false
      }
    }

    const refreshFileList = async () => {
      await loadFileList()
    }

    const openFile = async (filename) => {
      currentFilename.value = filename
      
      // 获取文件信息以确定标注类型
      try {
        const response = await axios.get(`/api/file/${filename}`)
        if (response.data && response.data.file_info) {
          currentAnnotationType.value = response.data.file_info.annotation_type || 'qa'
        }
      } catch (error) {
        console.error('获取文件信息失败:', error)
        currentAnnotationType.value = 'qa'  // 默认为QA标注
      }
      
      await loadData()
      await loadStats()
    }

    const deleteFile = async (filename) => {
      try {
        await ElMessageBox.confirm('确定要删除这个文件吗？删除后无法恢复。', '确认删除', {
          type: 'warning'
        })
        
        await axios.delete(`/api/file/${filename}`)
        ElMessage.success('文件删除成功')
        
        // 刷新文件列表
        await loadFileList()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除文件失败')
        }
      }
    }

    // 格式化日期时间
    const formatDateTime = (dateTimeStr) => {
      if (!dateTimeStr) return ''
      const date = new Date(dateTimeStr)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }

    // 上传对话框相关功能
    const showUploadDialog = () => {
      uploadDialog.visible = true
      uploadDialog.uploading = false
      uploadDialog.progress = 0
      uploadDialog.statusText = ''
    }

    const handleFileChangeInDialog = async (file) => {
      if (!file.raw.name.endsWith('.jsonl')) {
        ElMessage.error('请上传JSONL格式的文件')
        return
      }
      
      uploadDialog.uploading = true
      uploadDialog.progress = 0
      uploadDialog.statusText = '正在上传文件...'
      
      try {
        const formData = new FormData()
        formData.append('file', file.raw)
        formData.append('annotation_type', uploadDialog.annotationType)
        
        // 模拟上传进度
        const progressInterval = setInterval(() => {
          if (uploadDialog.progress < 90) {
            uploadDialog.progress += 10
          }
        }, 100)
        
        const response = await axios.post('/api/upload', formData)
        
        clearInterval(progressInterval)
        uploadDialog.progress = 100
        uploadDialog.statusText = '文件上传成功！'
        
        if (response.data) {
          const annotationTypeText = uploadDialog.annotationType === 'qa' ? 'QA标注' : '评分标注'
          ElMessage.success(`文件上传成功，共 ${response.data.total_count} 条数据（${annotationTypeText}）`)
          uploadDialog.visible = false
          
          // 刷新文件列表
          await loadFileList()
          
          // 自动打开上传的文件
          currentFilename.value = response.data.filename
          await loadData()
          await loadStats()
        }
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '上传失败')
        uploadDialog.statusText = '上传失败'
      } finally {
        setTimeout(() => {
          uploadDialog.uploading = false
          uploadDialog.progress = 0
          uploadDialog.statusText = ''
        }, 2000)
      }
    }

    // 显示导出对话框
    const showExportDialog = () => {
      if (!currentFilename.value) {
        ElMessage.error('请先选择一个文件')
        return
      }
      
      // 重置选择为有数据的类型
      if (stats.correct_count > 0) {
        exportDialog.selectedType = 'correct'
      } else if (stats.incorrect_count > 0) {
        exportDialog.selectedType = 'incorrect'
      } else {
        ElMessage.warning('没有已标注的数据可以导出')
        return
      }
      
      exportDialog.visible = true
    }

    // 确认导出
    const confirmExport = async () => {
      if (!exportDialog.selectedType) {
        ElMessage.error('请选择要导出的数据类型')
        return
      }
      
      // 检查是否有对应类型的数据可以导出
      const countToCheck = exportDialog.selectedType === 'correct' ? stats.correct_count : stats.incorrect_count
      const typeText = exportDialog.selectedType === 'correct' ? '正确' : '错误'
      
      if (countToCheck === 0) {
        ElMessage.warning(`没有标注${typeText}的数据可以导出`)
        return
      }
      
      exporting.value = true
      
      try {
        const export_name = `${exportDialog.selectedType}_data_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.jsonl`
        
        const response = await axios.post('/api/export', {
          filename: currentFilename.value,
          export_name: export_name,
          selected_only: false,  // 我们需要导出所有指定类型的数据
          export_type: exportDialog.selectedType
        })
        
        if (response.data) {
          ElMessage.success(`导出成功！共导出 ${response.data.export_count} 条${response.data.export_type}数据`)
          exportDialog.visible = false
          
          // 创建下载链接
          const downloadUrl = `/api/download/${response.data.export_path.split('/').pop()}`
          const link = document.createElement('a')
          link.href = downloadUrl
          link.download = response.data.export_path.split('/').pop()
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
        }
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '导出失败')
      } finally {
        exporting.value = false
      }
    }

    // 导出数据（保留原函数以备后用）
    const exportData = async () => {
      if (!currentFilename.value) {
        ElMessage.error('请先选择一个文件')
        return
      }
      
      // 检查是否有对应类型的数据可以导出
      const countToCheck = exportType.value === 'correct' ? stats.correct_count : stats.incorrect_count
      const typeText = exportType.value === 'correct' ? '正确' : '错误'
      
      if (countToCheck === 0) {
        ElMessage.warning(`没有标注${typeText}的数据可以导出`)
        return
      }
      
      exporting.value = true
      
      try {
        const export_name = `${exportType.value}_data_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.jsonl`
        
        const response = await axios.post('/api/export', {
          filename: currentFilename.value,
          export_name: export_name,
          selected_only: false,  // 我们需要导出所有指定类型的数据
          export_type: exportType.value
        })
        
        if (response.data) {
          ElMessage.success(`导出成功！共导出 ${response.data.export_count} 条${response.data.export_type}数据`)
          
          // 创建下载链接
          const downloadUrl = `/api/download/${response.data.export_path.split('/').pop()}`
          const link = document.createElement('a')
          link.href = downloadUrl
          link.download = response.data.export_path.split('/').pop()
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
        }
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '导出失败')
      } finally {
        exporting.value = false
      }
    }

    // 组件挂载时加载文件列表
    onMounted(() => {
      loadFileList()
    })

    return {
      loading,
      currentFilename,
      currentAnnotationType,
      dataList,
      stats,
      filters,
      pagination,
      fileList,
      filesLoading,
      uploadDialog,
      exporting,
      exportType,
      exportDialog,
      handleFileChange,
      applyFilters,
      debounceSearch,
      handlePageSizeChange,
      handlePageChange,
      updateItem,
      annotateItem,
      getCurrentFileName,
      backToHome,
      loadFileList,
      refreshFileList,
      openFile,
      deleteFile,
      formatDateTime,
      showUploadDialog,
      handleFileChangeInDialog,
      showExportDialog,
      confirmExport,
      exportData
    }
  }
}
</script>

<style>
/* 全局样式，移除默认边距 */
html, body {
  margin: 0 !important;
  padding: 0 !important;
  overflow-x: hidden;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
</style>

<style scoped>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  min-height: 100vh;
  background: #f5f7fa;
  margin: 0;
  padding: 0;
}

* {
  box-sizing: border-box;
}

/* 重置 Element Plus 容器的默认样式 */
.el-container {
  margin: 0 !important;
  padding: 0 !important;
  min-height: 100vh;
}

.el-header {
  padding: 0 !important;
  margin: 0 !important;
  height: auto !important;
}

.el-main {
  padding: 24px !important;
  margin: 0 !important;
}

.header {
  width: 100%;
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  color: white;
  padding: 0 !important;
  border-bottom: 3px solid #1a252f;
  position: relative;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.header-content {
  width: 100%;
  /* padding: 16px 18px; */
  margin: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.header-content h1 {
  font-size: 2.2rem;
  margin: 0;
  padding: 0;
  font-weight: 700;
  color: #ffffff;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  letter-spacing: 0.5px;
  text-align: center;
  width: 100%;
}

.header-content h1 .el-icon {
  font-size: 2.4rem;
}

.header-content p {
  font-size: 1.1rem;
  color: #f0f4ff;
  font-weight: 400;
  margin: 0;
  opacity: 0.95;
  text-align: center;
}

.main-content {
  padding: 24px;
  background: #f5f7fa;
  min-height: calc(100vh - 120px);
}

.upload-section {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.upload-card {
  width: 100%;
  max-width: 600px;
  margin-bottom: 20px;
}

.upload-dragger {
  width: 100%;
}

.files-card {
  width: 100%;
  max-width: 1200px;
  margin-bottom: 20px;
}

.files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.files-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.empty-files {
  padding: 40px 20px;
  text-align: center;
}

.upload-dialog-dragger {
  width: 100%;
}

.upload-progress {
  margin-top: 20px;
  text-align: center;
}

.upload-progress p {
  margin-top: 10px;
  color: #666;
  font-size: 14px;
}

/* 上传表单样式 */
.upload-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.annotation-type-section {
  padding-bottom: 20px;
  border-bottom: 1px solid #e9ecef;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 16px;
}

.section-label .el-icon {
  color: #2c3e50;
}

.upload-section {
  padding-top: 20px;
}

.annotation-type-radio {
  display: flex;
  width: 100%;
  margin-bottom: 12px;
  padding: 16px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.annotation-type-radio:hover {
  border-color: #409eff;
  background: #f0f9ff;
}

.annotation-type-radio.is-checked {
  border-color: #409eff;
  background: #f0f9ff;
}

.annotation-type-radio :deep(.el-radio__input) {
  margin-top: 2px;
  margin-right: 12px;
}

.radio-content {
  flex: 1;
}

.radio-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.radio-desc {
  font-size: 14px;
  color: #666;
  line-height: 1.4;
}

/* 简洁导出对话框样式 */
.simple-export-dialog :deep(.el-dialog) {
  border-radius: 8px;
}

.simple-export-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-section h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.form-section .el-radio-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.export-stats {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.stat-item:last-child {
  margin-bottom: 0;
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.stat-value.correct {
  background: #d4edda;
  color: #155724;
}

.stat-value.incorrect {
  background: #f8d7da;
  color: #721c24;
}

.filename-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filename-cell .el-icon {
  color: #2c3e50;
}

.file-info-card {
  margin-bottom: 20px;
  background: #ffffff;
  border: 1px solid #e1e8ed;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.file-info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
}

.file-info h2 {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  color: #2c3e50;
  font-size: 1.5rem;
  font-weight: 600;
}

.file-info h2 .el-icon {
  font-size: 1.8rem;
  color: #2c3e50;
}

.file-info-header .el-button {
  background: #2c3e50;
  border: 1px solid #2c3e50;
  color: #ffffff;
  font-weight: 500;
  padding: 12px 24px;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.file-info-header .el-button:hover {
  background: #34495e;
  border-color: #34495e;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.file-info-header .el-button .el-icon {
  margin-right: 8px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  background: #ffffff;
  color: #2c3e50;
  border: 1px solid #e1e8ed;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.stat-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.stat-card.selected {
  background: #d4edda;
  border-color: #c3e6cb;
  color: #155724;
}

.stat-card.unselected {
  background: #f8d7da;
  border-color: #f5c6cb;
  color: #721c24;
}

.stat-card.correct {
  background: #d4edda;
  border-color: #c3e6cb;
  color: #155724;
}

.stat-card.incorrect {
  background: #f8d7da;
  border-color: #f5c6cb;
  color: #721c24;
}

.stat-card.unannotated {
  background: #fff3cd;
  border-color: #ffeaa7;
  color: #856404;
}

.stat-content {
  padding: 20px;
}

.stat-number {
  font-size: 2rem;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 0.9rem;
  opacity: 0.9;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.filter-right {
  display: flex;
  align-items: center;
}

.filter-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.filter-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #666;
  margin-bottom: 0;
  white-space: nowrap;
}

.filter-label::after {
  content: ':';
  margin-left: 2px;
}

.export-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.data-card {
  min-height: 400px;
}

.data-list {
  min-height: 300px;
}

.no-data {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
}

.data-item {
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 15px;
  transition: all 0.3s ease;
  background: white;
}

.data-item:hover {
  box-shadow: 0 4px 15px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}

.data-item.selected {
  border-color: #28a745;
  background: #f8fff9;
}

.data-item.annotated-correct {
  border-color: #28a745;
  background: #f8fff9;
  box-shadow: 0 0 10px rgba(40, 167, 69, 0.2);
}

.data-item.annotated-incorrect {
  border-color: #dc3545;
  background: #fff8f8;
  box-shadow: 0 0 10px rgba(220, 53, 69, 0.2);
}

.data-item.hiding {
  animation: fadeOutScale 0.3s ease-out forwards;
  opacity: 0;
  transform: scale(0.95);
}

@keyframes fadeOutScale {
  0% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.98);
  }
  100% {
    opacity: 0;
    transform: scale(0.95);
  }
}

.data-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e9ecef;
}

.data-controls {
  display: flex;
  align-items: center;
  gap: 15px;
}

.quality-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.annotation-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.annotation-selector .el-radio-group {
  margin-left: 8px;
}

/* 评分选择器样式 */
.scoring-selector {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}

.scoring-selector .el-rate {
  margin-left: 8px;
}

.scoring-selector .el-button {
  margin-left: 8px;
  align-self: flex-start;
}

.data-content {
  display: grid;
  gap: 15px;
}

.data-field {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #2c3e50;
}

.field-label {
  font-weight: 600;
  color: #495057;
  margin-bottom: 5px;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.field-content {
  color: #333;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}


/* 简洁上传对话框样式 */
.simple-upload-dialog :deep(.el-dialog) {
  border-radius: 8px;
}

.simple-upload-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-section h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.form-section .el-radio-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.simple-upload-progress {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}
</style>
