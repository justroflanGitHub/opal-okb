
void __cdecl16far FUN_4000_92c4(int param_1,int param_2,int param_3,int param_4)

{
  undefined2 unaff_DS;
  
  if (*(char *)0x14ec != '\0') {
    FUN_4000_a53b();
    if (param_3 <= param_1) {
      param_1 = param_3;
    }
    if (param_4 <= param_2) {
      param_2 = param_4;
    }
    *(undefined1 *)0x6345 = 0;
    *(int *)0x6352 = param_1;
    *(int *)0x6354 = param_2;
    FUN_4000_931e();
  }
  return;
}

