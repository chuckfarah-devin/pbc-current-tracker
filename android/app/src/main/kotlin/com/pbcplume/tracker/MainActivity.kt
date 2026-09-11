package com.pbcplume.tracker

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.navigation.fragment.NavHostFragment
import com.pbcplume.tracker.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Theme is NoActionBar — nav graph only needs the host; system back
        // button handles Settings/Debug return navigation.
        supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
    }
}
