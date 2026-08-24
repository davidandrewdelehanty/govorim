// Desktop entry point. Mobile enters through `run()` in lib.rs directly.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    govorim_lib::run()
}
