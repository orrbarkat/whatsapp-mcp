package main

import (
	"os"
	"testing"
)

func TestExtractDirectPathFromURL(t *testing.T) {
	url := "https://mmg.whatsapp.net/v/t62.7118-24/13812002_698058036224062_3424455886509161511_n.enc?ccb=11-4&oh=abc"
	dp := extractDirectPathFromURL(url)
	if dp == "" || dp[0] != '/' {
		t.Fatalf("expected direct path starting with '/', got %q", dp)
	}
	if len(dp) == len(url) {
		t.Fatalf("expected direct path to differ from full URL, got same value: %q", dp)
	}
	if dp != "/v/t62.7118-24/13812002_698058036224062_3424455886509161511_n.enc" {
		t.Fatalf("unexpected direct path: %q", dp)
	}
}

func TestPlaceholderWaveform_LengthAndRange(t *testing.T) {
	wf := placeholderWaveform(10)
	if len(wf) != 64 {
		t.Fatalf("expected waveform length 64, got %d", len(wf))
	}
	for i, v := range wf {
		if v > 100 { // v is unsigned, only need upper bound
			t.Fatalf("waveform[%d]=%d out of range [0,100]", i, v)
		}
	}
}

func TestGetServerPort_FromEnv(t *testing.T) {
	old := os.Getenv("PORT")
	t.Cleanup(func() { _ = os.Setenv("PORT", old) })
	_ = os.Setenv("PORT", "9090")
	if p := getServerPort(); p != 9090 {
		t.Fatalf("expected 9090, got %d", p)
	}
}

func TestGetServerPort_Default(t *testing.T) {
	old := os.Getenv("PORT")
	t.Cleanup(func() { _ = os.Setenv("PORT", old) })
	_ = os.Unsetenv("PORT")
	if p := getServerPort(); p != 8080 {
		t.Fatalf("expected default 8080, got %d", p)
	}
}
