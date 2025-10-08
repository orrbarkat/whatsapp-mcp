package main

import "testing"

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
