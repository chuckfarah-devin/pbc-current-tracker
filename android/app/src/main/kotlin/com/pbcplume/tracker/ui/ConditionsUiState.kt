package com.pbcplume.tracker.ui

import com.pbcplume.tracker.data.model.ConditionsResponse

sealed interface ConditionsUiState {
    data object Loading : ConditionsUiState
    data class Success(val data: ConditionsResponse) : ConditionsUiState
    data class Error(val message: String) : ConditionsUiState
}
