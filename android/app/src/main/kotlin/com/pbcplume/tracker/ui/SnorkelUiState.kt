package com.pbcplume.tracker.ui

import com.pbcplume.tracker.data.model.SnorkelConditionsResponse

sealed interface SnorkelUiState {
    data object Loading : SnorkelUiState
    data class Success(val data: SnorkelConditionsResponse) : SnorkelUiState
    data class Error(val message: String) : SnorkelUiState
}
